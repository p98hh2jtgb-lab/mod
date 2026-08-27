-- This Source Code Form is subject to the terms of the bCDDL, v. 1.1.
-- If a copy of the bCDDL was not distributed with this
-- file, You can obtain one at http://beamng.com/bCDDL-1.1.txt

--[[
  execFunction.lua

  ファンクションを実行する共通コントローラー
  VLUA方式: mapmgr.getObjects()で自身の周囲をスキャンし、
  - VLUA実装済みGimmick: obj:queueObjectLuaCommand()で直接実行（GEをスキップ）
  - GE専用Gimmick(teleport/paintRandomColor/repair/openLatches): GEへ委譲
]]--

local M = {}

local DEFAULT_FUNCTION_NAME = "explode"

-- GE側のDASHFIELD_DISTANCEと一致させること
local DASHFIELD_SQUARED_DISTANCE = 3 * 3

local SLINGSHOT_COOLDOWN_SEC    = 3
local DOUBLE_SPEED_COOLDOWN_SEC = 2
local EXTINGUISH_COOLDOWN_SEC   = 1
local SPIN_POWER_COEF           = 5
local FLIP_POWER_COEF           = 10
local RANDOM_FUNCTION_TIMEOUT_SEC = 3
local MIN_FUNCTION_CHANCE_RATE    = 0.0001
local FUNCTION_CHANCE_VELOCITY_COEF = 0.0001
local BREAK_RANDOM_BASE_PROB      = 1e-5   -- breakRandomBreakGroups: 破壊確率の基底値
local BREAK_RANDOM_VEL_COEF       = 5e-6   -- breakRandomBreakGroups: 速度による確率増加係数

-- thrusters.applyVelocity の適用時間(秒)
-- 省略すると lastDt(直近の描画フレーム時間)が使われ、速度差分を1フレームに詰め込むため
-- 加速度が過大になる(かつFPSに依存して強さが変わる)。公式も tyreBarrier 等で明示的に指定している
local VELOCITY_RAMP_SEC           = 0.05

-- VLUA側で管理するステートテーブル
local slingshotState    = {} -- [vid] = {chargeEndTime, directionVector, dashSpeedMPS} or {cooldownUntil}
local fireworksState    = {} -- [vid] = {explodeTime}
local extinguishCooldowns = {} -- [vid] = cooldownEndTime
local scaleSpeedState   = {} -- [vid] = {targetVelocity, endTime}

-- randomのステート
local lastRandomFunc        = nil  -- {key, func}
local lastRandomTargetHash  = 0
local lastRandomTime        = 0.0

local updateIntervalPhysicsSec = 0.01
local cumulativePhysicsSteps = 0
local scanModeVehicle = false  -- trueのときupdateをスキップ

-- 性能測定（VLUA側）
local PERF_LOG_INTERVAL_SEC = 10
local perfVlua = { totalTime = 0.0, callCount = 0, lastLogTime = 0.0 }

local function logVluaPerf()
  if perfVlua.callCount == 0 then return end
  local now = os.clock()
  if now - perfVlua.lastLogTime < PERF_LOG_INTERVAL_SEC then return end
  log("I", "mathkuro_dashplate", string.format(
    "[PERF][VLUA-scan] %d calls in %.1fs | avg %.4f ms/call | total %.4f ms",
    perfVlua.callCount, PERF_LOG_INTERVAL_SEC,
    perfVlua.totalTime / perfVlua.callCount * 1000, perfVlua.totalTime * 1000))
  perfVlua.totalTime = 0.0
  perfVlua.callCount = 0
  perfVlua.lastLogTime = now
end

-- dashplateの向きベクトルをobjから直接計算（VLUA内ではobjがdashplate自身）
-- 前方ベクトルを右へ horizontalRad、上へ verticalRad 回転させた単位ベクトルを返す
local function adjustDashplateDirection(horizontalRad, verticalRad)
  if math.sin(verticalRad) == 1 then return vec3(0, 0, 1) end
  local fwd   = obj:getDirectionVector():normalized()
  local up    = obj:getDirectionVectorUp():normalized()
  local right = fwd:cross(up)
  local horizontalDir = fwd * math.cos(horizontalRad) + right * math.sin(horizontalRad)
  return (horizontalDir * math.cos(verticalRad) + up * math.sin(verticalRad)):normalized()
end

-- ターゲット車両の向きベクトルを計算するLua式を生成（コマンド文字列内で評価される）
local function makeDirExpr(horizontalRad, verticalRad)
  if math.sin(verticalRad) == 1 then return "vec3(0,0,1)" end
  local cosH, sinH = math.cos(horizontalRad), math.sin(horizontalRad)
  local cosV, sinV = math.cos(verticalRad), math.sin(verticalRad)
  return string.format(
    "(function()local f=obj:getDirectionVector():normalized()local u=obj:getDirectionVectorUp():normalized()local r=f:cross(u)return((f*%.6f+r*%.6f)*%.6f+u*%.6f):normalized()end)()",
    cosH, sinH, cosV, sinV)
end

-- =====================================================================
-- VLUA実装Gimmick関数テーブル
-- シグネチャ: function(vid, data, params)
--   vid   : ターゲット車両のID
--   data  : mapmgr.getObjects()の対象エントリ (data.pos, data.vel など)
--   params: JBeamから読み込んだパラメータテーブル
-- =====================================================================
local vluaFunctions = {}

vluaFunctions.breakHinges = function(vid)
  obj:queueObjectLuaCommand(vid, "beamstate.breakHinges()")
end

vluaFunctions.breakRandomBreakGroups = function(vid, _, params)
  params = params or {}
  local level = params.dashplateBreakFrequencyLevel or math.random(1, 100)
  -- ターゲットの速度はコマンド文字列内(target VLUA)で取得する
  obj:queueObjectLuaCommand(vid, string.format(
    "local vel=obj:getVelocity():length() local p=1-(%g+vel*%g)*%d " ..
    "for _,b in pairs(v.data.beams) do if b.breakGroup~=nil and math.random()>p then obj:breakBeam(b.cid) beamstate.breakBreakGroup(b.breakGroup) end end",
    BREAK_RANDOM_BASE_PROB, BREAK_RANDOM_VEL_COEF, level))
end

vluaFunctions.dash = function(vid, _, params)
  params = params or {}
  local speed = params.dashplateSpeedKMH and params.dashplateSpeedKMH / 3.6 or math.random(0, 1000)
  local hRad  = params.dashplateHorizontalDirectionDegree and math.rad(params.dashplateHorizontalDirectionDegree) or math.rad(math.random(-180, 180))
  local vRad  = params.dashplateVerticalAngleDegree and math.rad(params.dashplateVerticalAngleDegree) or math.rad(math.random(-90, 90))
  -- スムーズ発進: 加速を数秒に分散させる（省略時は従来の瞬間加速） / smooth catapult ramp (default = original instant snap)
  local rampSec = tonumber(params.dashplateDashRampSec) or VELOCITY_RAMP_SEC
  local dirExpr
  if params.dashplateUseDashplateDirection then
    dirExpr = serialize(adjustDashplateDirection(hRad, vRad))
  else
    dirExpr = makeDirExpr(hRad, vRad)
  end
  -- dash方向の速度成分だけを置き換え、それ以外（上下動・横方向）の成分は現在値を維持する。
  -- 速度ベクトル全体を上書きすると車体の上下動が毎回ゼロに固定され、
  -- Padの段差を乗り越えるサスペンションの動きを妨げてタイヤが破損する
  obj:queueObjectLuaCommand(vid, string.format(
    "local d=%s local v=obj:getVelocity() thrusters.applyVelocity(v-d*v:dot(d)+d*%.4f,%.4f)",
    dirExpr, speed, rampSec))
end

vluaFunctions.deflateTires = function(vid)
  obj:queueObjectLuaCommand(vid, "beamstate.deflateTires()")
end

vluaFunctions.deflateRandomTire = function(vid)
  obj:queueObjectLuaCommand(vid, "beamstate.deflateRandomTire()")
end

vluaFunctions.engineStall = function(vid)
  obj:queueObjectLuaCommand(vid, "electrics.setIgnitionLevel(0)")
end

vluaFunctions.explode = function(vid)
  obj:queueObjectLuaCommand(vid, "fire.explodeVehicle()")
  obj:queueObjectLuaCommand(vid, "beamstate.breakAllBreakgroups()")
end

vluaFunctions.extinguish = function(vid)
  local now = os.clock()
  if extinguishCooldowns[vid] and now < extinguishCooldowns[vid] then return end
  obj:queueObjectLuaCommand(vid, "fire.extinguishVehicle()")
  extinguishCooldowns[vid] = now + EXTINGUISH_COOLDOWN_SEC
end

vluaFunctions.fireworks = function(vid, _, params)
  if fireworksState[vid] then return end
  params = params or {}
  local speed = (params.dashplateFireworksSpeedKMH or 150) / 3.6
  local delay = params.dashplateFireworksDelaySec or 3
  obj:queueObjectLuaCommand(vid, string.format(
    "thrusters.applyVelocity(vec3(0,0,1) * %.4f,%.4f)", speed, VELOCITY_RAMP_SEC))
  fireworksState[vid] = { explodeTime = os.clock() + delay }
end

vluaFunctions.flip = function(vid, _, params)
  params = params or {}
  local rate = (params.dashplateFlipPowerPercent or math.random(-100, 100)) / 100 * FLIP_POWER_COEF
  obj:queueObjectLuaCommand(vid, string.format(
    "thrusters.applyAccel(obj:getDirectionVector(),nil,nil,obj:getDirectionVector()*(obj:getVelocity():length()+2)*%.4f)",
    rate))
end

vluaFunctions.frontFlip = function(vid, _, params)
  params = params or {}
  local rate = (params.dashplateFrontFlipPowerPercent or math.random(-100, 100)) / 100 * FLIP_POWER_COEF
  obj:queueObjectLuaCommand(vid, string.format(
    "thrusters.applyAccel(obj:getDirectionVector(),nil,nil,obj:getDirectionVector():cross(obj:getDirectionVectorUp())*(obj:getVelocity():length()+2)*%.4f)",
    rate))
end

vluaFunctions.horn = function(vid)
  obj:queueObjectLuaCommand(vid, "electrics.horn(true)")
end

vluaFunctions.ignite = function(vid)
  obj:queueObjectLuaCommand(vid, "fire.igniteVehicle()")
end

vluaFunctions.scaleSpeed = function(vid, data, params)
  params = params or {}
  local now = os.clock()
  local state = scaleSpeedState[vid]

  -- クールダウン中: 記録した速度ベクトルを適用し続ける
  if state then
    if now < state.endTime then
      obj:queueObjectLuaCommand(vid, string.format(
        "thrusters.applyVelocity(%s,%.4f)", serialize(state.targetVelocity), VELOCITY_RAMP_SEC))
      return
    end
    scaleSpeedState[vid] = nil
  end

  -- 初回接触: mapmgr経由でターゲットの速度を取得して倍率をかける
  local vel = data and data.vel
  if not vel then
    log("W", "mathkuro_dashplate", "scaleSpeed: data.vel is unavailable for vid=" .. vid)
    return
  end
  local multiplier = params.dashplateSpeedMultiplier or 2
  local targetVelocity = vel * multiplier
  scaleSpeedState[vid] = { targetVelocity = targetVelocity, endTime = now + DOUBLE_SPEED_COOLDOWN_SEC }
  obj:queueObjectLuaCommand(vid, string.format(
    "thrusters.applyVelocity(%s,%.4f)", serialize(targetVelocity), VELOCITY_RAMP_SEC))
end

vluaFunctions.slingshot = function(vid, _, params)
  params = params or {}
  local now = os.clock()
  local state = slingshotState[vid]

  if state and state.cooldownUntil then
    if now >= state.cooldownUntil then
      slingshotState[vid] = nil
      state = nil
    end
  end

  if not state then
    local speed = params.dashplateSpeedKMH and params.dashplateSpeedKMH / 3.6 or math.random(0, 1000)
    local hRad  = params.dashplateHorizontalDirectionDegree and math.rad(params.dashplateHorizontalDirectionDegree) or 0
    local vRad  = params.dashplateVerticalAngleDegree and math.rad(params.dashplateVerticalAngleDegree) or 0
    -- dashplateUseDashplateDirection == falseの場合もdashplate方向を使用
    -- （状態生成時点でのtarget方向はVLUAから取得不可のため）
    local dirVec = adjustDashplateDirection(hRad, vRad)
    state = {
      chargeEndTime   = now + (params.dashplateSlingshotChargeSec or 5),
      directionVector = dirVec,
      dashSpeedMPS    = speed,
    }
    state.cooldownUntil = state.chargeEndTime + SLINGSHOT_COOLDOWN_SEC
    slingshotState[vid] = state
  end

  if now < state.chargeEndTime then
    -- 引きフェーズ
    obj:queueObjectLuaCommand(vid, string.format(
      "thrusters.applyVelocity(vec3(0,0,0),%.4f)", VELOCITY_RAMP_SEC))
  else
    -- 放出フェーズ
    obj:queueObjectLuaCommand(vid, string.format(
      "thrusters.applyVelocity(%s * %.4f,%.4f)",
      serialize(state.directionVector), state.dashSpeedMPS, VELOCITY_RAMP_SEC))
  end
end

vluaFunctions.spin = function(vid, _, params)
  params = params or {}
  local rate = (params.dashplateSpinPowerPercent or math.random(-100, 100)) / 100 * SPIN_POWER_COEF
  obj:queueObjectLuaCommand(vid, string.format(
    "thrusters.applyAccel(obj:getDirectionVector(),nil,nil,obj:getDirectionVectorUp()*(obj:getVelocity():length()+2)*%.4f)",
    rate))
end

vluaFunctions.toggleLights = function(vid)
  obj:queueObjectLuaCommand(vid, "electrics.toggle_warn_signal() electrics.toggle_fog_lights() electrics.toggle_lights()")
end

vluaFunctions.tornado = function(vid, _, params)
  params = params or {}
  local spinRate   = (params.dashplateSpinPowerPercent or math.random(-100, 100)) / 100 * SPIN_POWER_COEF
  local upperSpeed = params.dashplateUpperSpeedKMH and params.dashplateUpperSpeedKMH / 3.6 or math.random(0, 1000)
  -- vehicleVectorのxy成分はターゲット自身のgetDirectionVectorからコマンド内で取得する
  obj:queueObjectLuaCommand(vid, string.format(
    "local d=obj:getDirectionVector() thrusters.applyAccel(vec3(d.x,d.y,%.4f),nil,nil,obj:getDirectionVectorUp()*(obj:getVelocity():length()+2)*%.4f)",
    upperSpeed, spinRate))
end

-- =====================================================================
-- random / all（VLUA実装済みGimmickのみ対象）
-- =====================================================================
local vluaRandomFunctions = {}

local function execRandom(vid, data, params)
  local myId = obj:getID()
  local targetHash = vid + myId
  local now = os.clock()

  -- 直近で同じ車両×dashplate組み合わせにランダム関数が実行済みなら、同じ効果を継続
  if lastRandomFunc and lastRandomTargetHash == targetHash and now - lastRandomTime < RANDOM_FUNCTION_TIMEOUT_SEC then
    lastRandomFunc.func(vid, data, params and params[lastRandomFunc.key] or {})
    return
  end

  local chosen = vluaRandomFunctions[math.random(1, #vluaRandomFunctions)]
  local subParams = params and params[chosen.key] or {}
  local chance = subParams.chance or 0
  if math.random() < chance / 100 then
    chosen.func(vid, data, subParams)
    lastRandomFunc       = chosen
    lastRandomTargetHash = targetHash
    lastRandomTime       = now
    obj:queueGameEngineLua(string.format(
      "guihooks.trigger('mathkuroDashplateCurrentFunction',%s)",
      serialize({dashplateVid = myId, targetVid = vid, functionName = chosen.key, params = subParams})))
    log("D", "mathkuro_dashplate", string.format(
      "Random: '%s' on vid=%d by dashplate=%d (chance=%.1f%%)", chosen.key, vid, myId, chance))
  end
end

local function execAll(vid, data, params)
  local vel = data and data.vel and data.vel:length() or 0
  local level = params and params.dashplateActivationLevel or 2
  local chanceRate = (MIN_FUNCTION_CHANCE_RATE + vel * FUNCTION_CHANCE_VELOCITY_COEF) * level
  if math.random() < chanceRate then
    for _, entry in pairs(vluaRandomFunctions) do
      entry.func(vid, data, {})
    end
  end
end

vluaFunctions.random = execRandom
vluaFunctions.all    = execAll

-- GE専用Gimmick（GEへ委譲）
table.insert(vluaRandomFunctions, {key = "dashplateRandomRepair",
  func = function(vid, _, params)
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. vid .. ",'repair'," .. serialize(params or {}) .. ")")
  end})
table.insert(vluaRandomFunctions, {key = "dashplateRandomTeleport",
  func = function(vid, _, params)
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. vid .. ",'teleport'," .. serialize(params or {}) .. ")")
  end})
table.insert(vluaRandomFunctions, {key = "dashplateRandomOpen",
  func = function(vid, _, _)
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. vid .. ",'openLatches',{})")
  end})
table.insert(vluaRandomFunctions, {key = "dashplateRandomPaint",
  func = function(vid, _, params)
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. vid .. ",'paintRandomColor'," .. serialize(params or {}) .. ")")
  end})

-- VLUA実装済みGimmick
table.insert(vluaRandomFunctions, {key = "dashplateRandomBreakHinges",    func = vluaFunctions.breakHinges})
table.insert(vluaRandomFunctions, {key = "dashplateRandomBreakRandom",    func = vluaFunctions.breakRandomBreakGroups})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDash",           func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashJump",       func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashOneWay",     func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashReverse",    func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashStop",       func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashTurnLeft",   func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDashTurnRight",  func = vluaFunctions.dash})
table.insert(vluaRandomFunctions, {key = "dashplateRandomDeflateTires",   func = vluaFunctions.deflateTires})
table.insert(vluaRandomFunctions, {key = "dashplateRandomExplode",        func = vluaFunctions.explode})
table.insert(vluaRandomFunctions, {key = "dashplateRandomExtinguish",     func = vluaFunctions.extinguish})
table.insert(vluaRandomFunctions, {key = "dashplateRandomIgnite",         func = vluaFunctions.ignite})
table.insert(vluaRandomFunctions, {key = "dashplateRandomFlip",           func = vluaFunctions.flip})
table.insert(vluaRandomFunctions, {key = "dashplateRandomFrontFlip",      func = vluaFunctions.frontFlip})
table.insert(vluaRandomFunctions, {key = "dashplateRandomToggleLights",   func = vluaFunctions.toggleLights})
table.insert(vluaRandomFunctions, {key = "dashplateRandomSlingshot",      func = vluaFunctions.slingshot})
table.insert(vluaRandomFunctions, {key = "dashplateRandomSpin",           func = vluaFunctions.spin})
table.insert(vluaRandomFunctions, {key = "dashplateRandomTornado",        func = vluaFunctions.tornado})
table.insert(vluaRandomFunctions, {key = "dashplateRandomFireworks",      func = vluaFunctions.fireworks})
table.insert(vluaRandomFunctions, {key = "dashplateRandomScaleSpeed",     func = vluaFunctions.scaleSpeed})

-- =====================================================================
-- キャッシュ
-- =====================================================================
local cachedFunctionName = nil
local cachedParamsStr    = nil
local cachedParams       = nil  -- デシリアライズ済みテーブル（VLUA関数に渡す）
local cachedVluaFunc     = nil  -- vluaFunctions[functionName]、またはnil（GE委譲）
local cachedGeSuffix     = nil  -- GE委譲時の queueGameEngineLua 文字列後半部分


local function setParam(paramName, value)
  local _params = deserialize(electrics.values.dashplateFunctionParamsStr) or {}
  _params[paramName] = value
  electrics.values.dashplateFunctionParamsStr = serialize(_params)
end

local function update(dtPhys)
  if scanModeVehicle then return end
  cumulativePhysicsSteps = cumulativePhysicsSteps + dtPhys
  if cumulativePhysicsSteps < updateIntervalPhysicsSec then return end
  cumulativePhysicsSteps = 0

  local t0  = os.clock()
  local now = t0

  -- fireworksのタイマーチェック（範囲外の車両も対象）
  for vid, state in pairs(fireworksState) do
    if now >= state.explodeTime then
      obj:queueObjectLuaCommand(vid, "fire.explodeVehicle()")
      obj:queueObjectLuaCommand(vid, "beamstate.breakAllBreakgroups()")
      fireworksState[vid] = nil
    end
  end

  -- 期限切れステートのクリア（メモリリーク防止）
  for vid, state in pairs(scaleSpeedState) do
    if now >= state.endTime then scaleSpeedState[vid] = nil end
  end
  for vid, t in pairs(extinguishCooldowns) do
    if now >= t then extinguishCooldowns[vid] = nil end
  end

  -- キャッシュ更新（functionNameまたはparamsStrが変化した場合のみ）
  local functionName = electrics.values.dashplateFunctionName
  local paramsStr    = electrics.values.dashplateFunctionParamsStr
  if functionName ~= cachedFunctionName or paramsStr ~= cachedParamsStr then
    cachedFunctionName = functionName
    cachedParamsStr    = paramsStr
    cachedParams       = deserialize(paramsStr) or {}
    cachedVluaFunc     = vluaFunctions[functionName]
    if not cachedVluaFunc then
      cachedGeSuffix = ", '" .. functionName .. "', " .. paramsStr .. ")"
    end
  end

  -- 近傍車両のスキャン
  local myId  = obj:getID()
  local myPos = obj:getPosition()

  -- トリガー半径（XLパッド用に設定可能 / per-pad trigger radius, default 3m）
  local triggerRadius = tonumber(cachedParams and cachedParams.dashplateTriggerRadius) or 3
  local triggerSquaredDistance = triggerRadius * triggerRadius

  if cachedVluaFunc then
    -- VLUA直接実行（GEをスキップ）
    for vid, data in pairs(mapmgr.getObjects() or {}) do
      if vid ~= myId and myPos:squaredDistance(data.pos) < triggerSquaredDistance then
        cachedVluaFunc(vid, data, cachedParams)
      end
    end
  else
    -- GE委譲（teleport, paintRandomColor, repair, openLatches）
    local suffix = cachedGeSuffix
    for vid, data in pairs(mapmgr.getObjects() or {}) do
      if vid ~= myId and myPos:squaredDistance(data.pos) < triggerSquaredDistance then
        obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. vid .. suffix)
      end
    end
  end

  --[[
  perfVlua.totalTime = perfVlua.totalTime + (os.clock() - t0)
  perfVlua.callCount = perfVlua.callCount + 1
  logVluaPerf()
  ]]--
end

local function init(jbeamData)
  -- ランダムのシードを初期化（dashplate毎に別シードを使用したいので、objのIDを加算）
  math.randomseed(os.time() + obj:getID())

  -- 通過した車両に影響を与える処理はGE側に実装しているのでロードする
  obj:queueGameEngineLua("if not mathkuro_dashplate then extensions.load('mathkuro_dashplate') end")

  electrics.values.dashplateFunctionName = jbeamData.dashplateFunctionName or DEFAULT_FUNCTION_NAME

  -- テレポートゲートの登録（スポーン時に1回だけ実行）
  if electrics.values.dashplateFunctionName == "teleport" and jbeamData.dashplateTeleportGateNumber and jbeamData.dashplateTeleportGateNumber > 0 then
    local role = jbeamData.dashplateTeleportGateRole or 0
    obj:queueGameEngineLua("mathkuro_dashplate.registerTeleportGate(" .. obj:getID() .. ", " .. jbeamData.dashplateTeleportGateNumber .. ", " .. role .. ")")
  end

  -- dashplate関連のパラメータを整形
  local params = {}
  for k, v in pairs(jbeamData) do
    if string.sub(k, 1, 19) == "dashplateRandomDash" or string.sub(k, 1, 24) == "dashplateRandomSlingshot" or k == "dashplateRandomTeleport" then
      local randomParams = deepcopy(v)
      randomParams.dashplateVid = obj:getID()
      params[k] = randomParams
    elseif string.sub(k, 1, 9) == "dashplate" and k ~= "dashplateFunctionName" then
      params[k] = v
    end
  end
  params["dashplateVid"] = obj:getID()

  electrics.values.dashplateFunctionParamsStr = serialize(params)
  log("D", "mathkuro_dashplate", "Initialized with function name: " .. electrics.values.dashplateFunctionName .. ", params: " .. electrics.values.dashplateFunctionParamsStr)

  -- キャッシュとステートを初期化
  cachedFunctionName = nil
  cachedParamsStr    = nil
  cachedParams       = nil
  cachedVluaFunc     = nil
  cachedGeSuffix     = nil
  cumulativePhysicsSteps = 0

  slingshotState    = {}
  fireworksState    = {}
  extinguishCooldowns = {}
  scaleSpeedState   = {}
  lastRandomFunc       = nil
  lastRandomTargetHash = 0
  lastRandomTime       = 0.0
end

local REGISTRY_UPDATE_INTERVAL_SEC = 3
local lastRegisteredTime = -math.huge

local function registerDashplate()
  local pos   = obj:getPosition()
  local dir   = obj:getDirectionVector()
  local dirUp = obj:getDirectionVectorUp()
  obj:queueGameEngineLua(string.format(
    "mathkuro_dashplate.registerDashplate(%d,{x=%.4f,y=%.4f,z=%.4f},{x=%.6f,y=%.6f,z=%.6f},{x=%.6f,y=%.6f,z=%.6f},'%s',%s)",
    obj:getID(),
    pos.x, pos.y, pos.z,
    dir.x, dir.y, dir.z,
    dirUp.x, dirUp.y, dirUp.z,
    electrics.values.dashplateFunctionName,
    electrics.values.dashplateFunctionParamsStr))
  lastRegisteredTime = os.clock()
end

local function updateGFX()
  if scanModeVehicle == false or os.clock() - lastRegisteredTime < REGISTRY_UPDATE_INTERVAL_SEC then return end
  registerDashplate()
end

local function applyScanMode(mode)
  mode = (mode or ''):match('^%s*(.-)%s*$')
  log("D", "mathkuro_dashplate", "Applying scan mode: '" .. mode .. "'(vid=" .. obj:getID() .. ")")
  if mode == 'vehicle' then
    scanModeVehicle = true
    registerDashplate()
  else
    scanModeVehicle = false
  end
end

M.setParam = setParam
M.applyScanMode = applyScanMode
M.forceRegister = registerDashplate

M.updateGFX = updateGFX
M.update = update
M.init = init


--Mandatory controller parameters
M.type = "main"
M.relevantDevice = nil
M.engineInfo = {}
M.gearboxInfo = {isReverse = false}
M.fireEngineTemperature = 0
M.throttle = 0
M.brake = 0
M.clutchRatio = 0
-------------------------------
--Mandatory main controller API
M.shiftUp = nop
M.shiftDown = nop
M.shiftToGearIndex = nop
M.cycleGearboxModes = nop
M.setGearboxMode = nop
M.setStarter = nop
M.setEngineIgnition = nop
M.setFreeze = nop
M.sendTorqueData = nop
M.vehicleActivated = nop
-------------------------------
return M
