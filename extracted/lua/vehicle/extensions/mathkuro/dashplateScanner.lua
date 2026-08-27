-- This Source Code Form is subject to the terms of the bCDDL, v. 1.1.
-- If a copy of the bCDDL was not distributed with this
-- file, You can obtain one at http://beamng.com/bCDDL-1.1.txt

--[[
  dashplateScanner.lua

  車両側VLUA方式: 車両が自身の周囲のdashplateをスキャンし、
  範囲内にいれば自車にGimmickを直接適用する。
  dashplate情報はmailbox経由で取得する。
]]--

local M = {}
local logTag = 'mathkuro_dashplate_scanner'

local DASHFIELD_SQUARED_DISTANCE    = 3 * 3
local MAILBOX_ADDRESS               = 'mathkuro_dashplate_registry'
local MAILBOX_REFRESH_INTERVAL_SEC  = 3

local SLINGSHOT_COOLDOWN_SEC        = 3
local DOUBLE_SPEED_COOLDOWN_SEC     = 2
local EXTINGUISH_COOLDOWN_SEC       = 1
local SPIN_POWER_COEF               = 5
local FLIP_POWER_COEF               = 10
local RANDOM_FUNCTION_TIMEOUT_SEC   = 3
local MIN_FUNCTION_CHANCE_RATE      = 0.0001
local FUNCTION_CHANCE_VELOCITY_COEF = 0.0001
local BREAK_RANDOM_BASE_PROB        = 1e-6
local BREAK_RANDOM_VEL_COEF         = 5e-7

-- thrusters.applyVelocity の適用時間(秒)
-- 省略すると lastDt(直近の描画フレーム時間)が使われ、速度差分を1フレームに詰め込むため
-- 加速度が過大になる(かつFPSに依存して強さが変わる)。公式も tyreBarrier 等で明示的に指定している
local VELOCITY_RAMP_SEC             = 0.05

-- ステート（dashplate VIDをキーに管理）
local slingshotState      = {}  -- [dashplateVid] = {chargeEndTime, directionVector, dashSpeedMPS} or {cooldownUntil}
local fireworksState      = {}  -- [dashplateVid] = {explodeTime}
local extinguishCooldowns = {}  -- [dashplateVid] = cooldownEndTime
local scaleSpeedState     = {}  -- [dashplateVid] = {targetVelocity, endTime}
local randomState         = {}  -- [dashplateVid] = {lastFunc, lastTime}

-- mailboxキャッシュ
local cachedDashplates   = {}
local lastMailboxRefresh = -math.huge

-- 物理スレッド間引き
M.updateIntervalPhysicsSec = 0.01
local cumulativePhysicsSteps   = 0

-- 性能測定
local PERF_LOG_INTERVAL_SEC = 10
local perfScanner = { totalTime = 0.0, callCount = 0, lastLogTime = 0.0 }

local function logScannerPerf()
  if perfScanner.callCount == 0 then return end
  local now = os.clock()
  if now - perfScanner.lastLogTime < PERF_LOG_INTERVAL_SEC then return end
  log("I", logTag, string.format(
    "[PERF][Scanner-%d] %d calls in %.1fs | avg %.4f ms/call | total %.4f ms",
    obj:getID(), perfScanner.callCount, PERF_LOG_INTERVAL_SEC,
    perfScanner.totalTime / perfScanner.callCount * 1000, perfScanner.totalTime * 1000))
  perfScanner.totalTime  = 0.0
  perfScanner.callCount  = 0
  perfScanner.lastLogTime = now
end

-- 前方ベクトルを右方向へ hRad、上方向へ vRad 回転させた単位ベクトルを返す
local function rotateDir(fwd, up, hRad, vRad)
  if math.sin(vRad) == 1 then return vec3(0, 0, 1) end
  local right = fwd:cross(up)
  local horizontalDir = fwd * math.cos(hRad) + right * math.sin(hRad)
  return (horizontalDir * math.cos(vRad) + up * math.sin(vRad)):normalized()
end

-- dashplateの向きベクトル（mailboxから取得した値を使用）
local function adjustDashplateDir(dashplate, hRad, vRad)
  local fwd = vec3(dashplate.dirVec.x, dashplate.dirVec.y, dashplate.dirVec.z):normalized()
  local up  = vec3(dashplate.dirVecUp.x, dashplate.dirVecUp.y, dashplate.dirVecUp.z):normalized()
  return rotateDir(fwd, up, hRad, vRad)
end

-- 車両自身の向きベクトル
local function adjustVehicleDir(hRad, vRad)
  return rotateDir(obj:getDirectionVector():normalized(), obj:getDirectionVectorUp():normalized(), hRad, vRad)
end

-- =====================================================================
-- Gimmick関数テーブル（自車への直接適用）
-- シグネチャ: function(dashplateVid, params, dashplate)
-- =====================================================================
local scannerFunctions = {}

scannerFunctions.breakHinges = function()
  beamstate.breakHinges()
end

scannerFunctions.breakRandomBreakGroups = function(dashplateVid, params)
  params = params or {}
  local level = params.dashplateBreakFrequencyLevel or math.random(1, 100)
  local vel = obj:getVelocity():length()
  local p = 1 - (BREAK_RANDOM_BASE_PROB + vel * BREAK_RANDOM_VEL_COEF) * level
  for _, b in pairs(v.data.beams) do
    if b.breakGroup ~= nil and math.random() > p then
      obj:breakBeam(b.cid)
      beamstate.breakBreakGroup(b.breakGroup)
    end
  end
end

scannerFunctions.dash = function(dashplateVid, params, dashplate)
  params = params or {}
  local speed = params.dashplateSpeedKMH and params.dashplateSpeedKMH / 3.6 or math.random(0, 1000)
  local hRad  = params.dashplateHorizontalDirectionDegree and math.rad(params.dashplateHorizontalDirectionDegree) or math.rad(math.random(-180, 180))
  local vRad  = params.dashplateVerticalAngleDegree and math.rad(params.dashplateVerticalAngleDegree) or math.rad(math.random(-90, 90))
  local dir
  if params.dashplateUseDashplateDirection then
    dir = adjustDashplateDir(dashplate, hRad, vRad)
  else
    dir = adjustVehicleDir(hRad, vRad)
  end
  -- dash方向の速度成分だけを置き換え、それ以外（上下動・横方向）の成分は現在値を維持する。
  -- 速度ベクトル全体を上書きすると車体の上下動が毎回ゼロに固定され、
  -- Padの段差を乗り越えるサスペンションの動きを妨げてタイヤが破損する
  local vel = obj:getVelocity()
  thrusters.applyVelocity(vel - dir * vel:dot(dir) + dir * speed, VELOCITY_RAMP_SEC)
end

scannerFunctions.deflateTires = function()
  beamstate.deflateTires()
end

scannerFunctions.deflateRandomTire = function()
  beamstate.deflateRandomTire()
end

scannerFunctions.engineStall = function()
  electrics.setIgnitionLevel(0)
end

scannerFunctions.explode = function()
  fire.explodeVehicle()
  beamstate.breakAllBreakgroups()
end

scannerFunctions.extinguish = function(dashplateVid)
  local now = os.clock()
  if extinguishCooldowns[dashplateVid] and now < extinguishCooldowns[dashplateVid] then return end
  fire.extinguishVehicle()
  extinguishCooldowns[dashplateVid] = now + EXTINGUISH_COOLDOWN_SEC
end

scannerFunctions.fireworks = function(dashplateVid, params)
  if fireworksState[dashplateVid] then return end
  params = params or {}
  local speed = (params.dashplateFireworksSpeedKMH or 150) / 3.6
  local delay = params.dashplateFireworksDelaySec or 3
  thrusters.applyVelocity(vec3(0, 0, 1) * speed, VELOCITY_RAMP_SEC)
  fireworksState[dashplateVid] = { explodeTime = os.clock() + delay }
end

scannerFunctions.flip = function(dashplateVid, params)
  params = params or {}
  local rate = (params.dashplateFlipPowerPercent or math.random(-100, 100)) / 100 * FLIP_POWER_COEF
  local fwd = obj:getDirectionVector()
  thrusters.applyAccel(fwd, nil, nil, fwd * (obj:getVelocity():length() + 2) * rate)
end

scannerFunctions.frontFlip = function(dashplateVid, params)
  params = params or {}
  local rate = (params.dashplateFrontFlipPowerPercent or math.random(-100, 100)) / 100 * FLIP_POWER_COEF
  local fwd = obj:getDirectionVector()
  thrusters.applyAccel(fwd, nil, nil, fwd:cross(obj:getDirectionVectorUp()) * (obj:getVelocity():length() + 2) * rate)
end

scannerFunctions.horn = function()
  electrics.horn(true)
end

scannerFunctions.ignite = function()
  fire.igniteVehicle()
end

scannerFunctions.scaleSpeed = function(dashplateVid, params)
  params = params or {}
  local now   = os.clock()
  local state = scaleSpeedState[dashplateVid]

  if state then
    if now < state.endTime then
      thrusters.applyVelocity(state.targetVelocity, VELOCITY_RAMP_SEC)
      return
    end
    scaleSpeedState[dashplateVid] = nil
  end

  local vel        = obj:getVelocity()
  local multiplier = params.dashplateSpeedMultiplier or 2
  local targetVel  = vel * multiplier
  scaleSpeedState[dashplateVid] = { targetVelocity = targetVel, endTime = now + DOUBLE_SPEED_COOLDOWN_SEC }
  thrusters.applyVelocity(targetVel, VELOCITY_RAMP_SEC)
end

scannerFunctions.slingshot = function(dashplateVid, params, dashplate)
  params = params or {}
  local now   = os.clock()
  local state = slingshotState[dashplateVid]

  if state and state.cooldownUntil then
    if now >= state.cooldownUntil then
      slingshotState[dashplateVid] = nil
      state = nil
    end
  end

  if not state then
    local speed = params.dashplateSpeedKMH and params.dashplateSpeedKMH / 3.6 or math.random(0, 1000)
    local hRad  = params.dashplateHorizontalDirectionDegree and math.rad(params.dashplateHorizontalDirectionDegree) or 0
    local vRad  = params.dashplateVerticalAngleDegree and math.rad(params.dashplateVerticalAngleDegree) or 0
    local dir   = adjustDashplateDir(dashplate, hRad, vRad)
    state = {
      chargeEndTime   = now + (params.dashplateSlingshotChargeSec or 5),
      directionVector = dir,
      dashSpeedMPS    = speed,
    }
    state.cooldownUntil = state.chargeEndTime + SLINGSHOT_COOLDOWN_SEC
    slingshotState[dashplateVid] = state
  end

  if now < state.chargeEndTime then
    thrusters.applyVelocity(vec3(0, 0, 0), VELOCITY_RAMP_SEC)
  else
    thrusters.applyVelocity(state.directionVector * state.dashSpeedMPS, VELOCITY_RAMP_SEC)
  end
end

scannerFunctions.spin = function(dashplateVid, params)
  params = params or {}
  local rate = (params.dashplateSpinPowerPercent or math.random(-100, 100)) / 100 * SPIN_POWER_COEF
  thrusters.applyAccel(obj:getDirectionVector(), nil, nil, obj:getDirectionVectorUp() * (obj:getVelocity():length() + 2) * rate)
end

scannerFunctions.toggleLights = function()
  electrics.toggle_warn_signal()
  electrics.toggle_fog_lights()
  electrics.toggle_lights()
end

scannerFunctions.tornado = function(dashplateVid, params)
  params = params or {}
  local spinRate   = (params.dashplateSpinPowerPercent or math.random(-100, 100)) / 100 * SPIN_POWER_COEF
  local upperSpeed = params.dashplateUpperSpeedKMH and params.dashplateUpperSpeedKMH / 3.6 or math.random(0, 1000)
  local d = obj:getDirectionVector()
  thrusters.applyAccel(vec3(d.x, d.y, upperSpeed), nil, nil, obj:getDirectionVectorUp() * (obj:getVelocity():length() + 2) * spinRate)
end

-- =====================================================================
-- random / all
-- =====================================================================
local scannerRandomFunctions = {}

-- GE専用Gimmick（GEへ委譲）
table.insert(scannerRandomFunctions, {key = "dashplateRandomRepair",
  func = function(_, params, _)
    local myId = obj:getID()
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. myId .. ",'repair'," .. serialize(params or {}) .. ")")
  end})
table.insert(scannerRandomFunctions, {key = "dashplateRandomTeleport",
  func = function(_, params, _)
    local myId = obj:getID()
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. myId .. ",'teleport'," .. serialize(params or {}) .. ")")
  end})
table.insert(scannerRandomFunctions, {key = "dashplateRandomOpen",
  func = function(_, _, _)
    local myId = obj:getID()
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. myId .. ",'openLatches',{})")
  end})
table.insert(scannerRandomFunctions, {key = "dashplateRandomPaint",
  func = function(_, params, _)
    local myId = obj:getID()
    obj:queueGameEngineLua("mathkuro_dashplate.executeOnVehicle(" .. myId .. ",'paintRandomColor'," .. serialize(params or {}) .. ")")
  end})

-- VLUA実装済みGimmick
table.insert(scannerRandomFunctions, {key = "dashplateRandomBreakHinges",    func = scannerFunctions.breakHinges})
table.insert(scannerRandomFunctions, {key = "dashplateRandomBreakRandom",    func = scannerFunctions.breakRandomBreakGroups})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDash",           func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashJump",       func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashOneWay",     func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashReverse",    func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashStop",       func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashTurnLeft",   func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDashTurnRight",  func = scannerFunctions.dash})
table.insert(scannerRandomFunctions, {key = "dashplateRandomDeflateTires",   func = scannerFunctions.deflateTires})
table.insert(scannerRandomFunctions, {key = "dashplateRandomExplode",        func = scannerFunctions.explode})
table.insert(scannerRandomFunctions, {key = "dashplateRandomExtinguish",     func = scannerFunctions.extinguish})
table.insert(scannerRandomFunctions, {key = "dashplateRandomIgnite",         func = scannerFunctions.ignite})
table.insert(scannerRandomFunctions, {key = "dashplateRandomFlip",           func = scannerFunctions.flip})
table.insert(scannerRandomFunctions, {key = "dashplateRandomFrontFlip",      func = scannerFunctions.frontFlip})
table.insert(scannerRandomFunctions, {key = "dashplateRandomToggleLights",   func = scannerFunctions.toggleLights})
table.insert(scannerRandomFunctions, {key = "dashplateRandomSlingshot",      func = scannerFunctions.slingshot})
table.insert(scannerRandomFunctions, {key = "dashplateRandomSpin",           func = scannerFunctions.spin})
table.insert(scannerRandomFunctions, {key = "dashplateRandomTornado",        func = scannerFunctions.tornado})
table.insert(scannerRandomFunctions, {key = "dashplateRandomFireworks",      func = scannerFunctions.fireworks})
table.insert(scannerRandomFunctions, {key = "dashplateRandomScaleSpeed",     func = scannerFunctions.scaleSpeed})

local function execRandom(dashplateVid, params, dashplate)
  local now   = os.clock()
  local state = randomState[dashplateVid]

  if state and state.lastFunc and now - state.lastTime < RANDOM_FUNCTION_TIMEOUT_SEC then
    state.lastFunc.func(dashplateVid, params and params[state.lastFunc.key] or {}, dashplate)
    return
  end

  local chosen    = scannerRandomFunctions[math.random(1, #scannerRandomFunctions)]
  local subParams = params and params[chosen.key] or {}
  local chance    = subParams.chance or 0
  if math.random() < chance / 100 then
    chosen.func(dashplateVid, subParams, dashplate)
    randomState[dashplateVid] = { lastFunc = chosen, lastTime = now }
    local myId = obj:getID()
    obj:queueGameEngineLua(string.format(
      "guihooks.trigger('mathkuroDashplateCurrentFunction',%s)",
      serialize({dashplateVid = dashplateVid, targetVid = myId, functionName = chosen.key, params = subParams})))
    log("D", logTag, string.format(
      "Random: '%s' on self (vid=%d) by dashplate=%d (chance=%.1f%%)", chosen.key, myId, dashplateVid, chance))
  end
end

local function execAll(dashplateVid, params, dashplate)
  local vel       = obj:getVelocity():length()
  local level     = params and params.dashplateActivationLevel or 2
  local chanceRate = (MIN_FUNCTION_CHANCE_RATE + vel * FUNCTION_CHANCE_VELOCITY_COEF) * level
  if math.random() < chanceRate then
    for _, entry in pairs(scannerRandomFunctions) do
      entry.func(dashplateVid, {}, dashplate)
    end
  end
end

-- GE専用Gimmick（scanner非対応 → GEへ委譲）
local geGimmicks = { teleport = true, paintRandomColor = true, repair = true, openLatches = true }

local function applyGimmick(dashplate)
  local dashplateVid = dashplate.vid
  local functionName = dashplate.functionName
  local params       = dashplate.params

  if functionName == 'random' then
    execRandom(dashplateVid, params, dashplate)
  elseif functionName == 'all' then
    execAll(dashplateVid, params, dashplate)
  elseif geGimmicks[functionName] then
    obj:queueGameEngineLua(string.format(
      "mathkuro_dashplate.executeOnVehicle(%d,'%s',%s)",
      obj:getID(), functionName, serialize(params or {})))
  else
    local func = scannerFunctions[functionName]
    if func then
      func(dashplateVid, params, dashplate)
    else
      log("W", logTag, "Unknown gimmick: " .. tostring(functionName))
    end
  end
end

local function update(dtPhys)
  cumulativePhysicsSteps = cumulativePhysicsSteps + dtPhys
  if cumulativePhysicsSteps < M.updateIntervalPhysicsSec then return end
  cumulativePhysicsSteps = 0

  local t0  = os.clock()
  local now = t0

  -- fireworksのタイマーチェック
  for dashplateVid, state in pairs(fireworksState) do
    if now >= state.explodeTime then
      fire.explodeVehicle()
      beamstate.breakAllBreakgroups()
      fireworksState[dashplateVid] = nil
    end
  end

  -- 期限切れステートのクリア
  for dashplateVid, state in pairs(scaleSpeedState) do
    if now >= state.endTime then scaleSpeedState[dashplateVid] = nil end
  end
  for dashplateVid, t in pairs(extinguishCooldowns) do
    if now >= t then extinguishCooldowns[dashplateVid] = nil end
  end

  -- mailboxキャッシュの更新（低頻度）
  if now - lastMailboxRefresh >= MAILBOX_REFRESH_INTERVAL_SEC then
    cachedDashplates = deserialize(obj:getLastMailbox(MAILBOX_ADDRESS)) or {}
    lastMailboxRefresh = now
  end

  -- 距離チェックとGimmick適用
  local myPos = obj:getPosition()
  for _, dashplate in ipairs(cachedDashplates) do
    local dpPos = vec3(dashplate.pos.x, dashplate.pos.y, dashplate.pos.z)
    if myPos:squaredDistance(dpPos) < DASHFIELD_SQUARED_DISTANCE then
      applyGimmick(dashplate)
    end
  end

  --[[
  perfScanner.totalTime = perfScanner.totalTime + (os.clock() - t0)
  perfScanner.callCount = perfScanner.callCount + 1
  logScannerPerf()
  ]]--
end

local function onExtensionLoaded()
  enablePhysicsStepHook()
  M.onPhysicsStep = update
end

M.onPhysicsStep = nop
M.updateGFX = nop
M.onExtensionLoaded = onExtensionLoaded

return M
