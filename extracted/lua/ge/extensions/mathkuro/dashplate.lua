-- This Source Code Form is subject to the terms of the bCDDL, v. 1.1.
-- If a copy of the bCDDL was not distributed with this
-- file, You can obtain one at http://beamng.com/bCDDL-1.1.txt

local M = {}
local logTag = 'mathkuro'

local DASHFIELD_DISTANCE = 3
local TELEPORT_COOLDOWN_SEC = 5

local repairState = {}         -- [targetVid] = lastRepairTime
local teleportGateRegistry = {} -- [gateNumber] = {vid, ...} (role=0 or 2 のみ登録)
local teleportGateRoles = {}   -- [dashplateVid] = role (0: 出入口両用, 1: 入口専用, 2: 出口専用)
local teleportCooldowns = {}   -- [targetVid] = cooldownEndTime
local dashplateRegistry = {}   -- [vid] = {vid, pos, dirVec, dirVecUp, functionName, params}
local scanMode = 'dashplate'   -- 'dashplate' | 'vehicle'

local function sendRegistryToMailbox()
  local list = {}
  for _, entry in pairs(dashplateRegistry) do
    table.insert(list, entry)
  end
  be:sendToMailbox('mathkuro_dashplate_registry', serialize(list))
end

local function registerDashplate(vid, pos, dirVec, dirVecUp, functionName, params)
  dashplateRegistry[vid] = {
    vid          = vid,
    pos          = pos,
    dirVec       = dirVec,
    dirVecUp     = dirVecUp,
    functionName = functionName,
    params       = params,
  }
  sendRegistryToMailbox()
end

local function getDashplateRegistry()
  return dashplateRegistry
end

local function onVehicleSpawned(vid)
  local veh = be:getObjectByID(vid)
  if not veh then return end

  if veh.JBeam == 'dashplate_mathkuro' then
    veh:queueLuaCommand("controller.getController('executeFunction').applyScanMode('" .. scanMode .. "')")
  elseif scanMode == 'vehicle' then
    veh:queueLuaCommand("extensions.load('mathkuro_dashplateScanner')")
  end
end

local function getScanMode()
  return scanMode
end

local function onExtensionLoaded()
  dashplateRegistry = {}
  teleportGateRoles = {}
  scanMode = 'dashplate'
  for _, veh in activeVehiclesIterator() do
    if veh.JBeam == 'dashplate_mathkuro' then
      -- dashplateモードにリセットし、レジストリを再登録
      veh:queueLuaCommand("controller.getController('executeFunction').applyScanMode('dashplate')")
      veh:queueLuaCommand("controller.getController('executeFunction').forceRegister()")
    else
      -- 車両側のscannerをアンロード
      veh:queueLuaCommand("extensions.unload('mathkuro_dashplateScanner')")
    end
  end
  log('D', logTag, 'onExtensionLoaded: registry cleared, scan mode reset to dashplate')
end

local function setScanMode(mode)
  if mode ~= 'dashplate' and mode ~= 'vehicle' then
    log('W', logTag, 'setScanMode: unknown mode: ' .. tostring(mode))
    return
  end
  if scanMode == mode then return end
  scanMode = mode

  for _, veh in activeVehiclesIterator() do
    -- 全車両（dashplate以外）にscannerをロード/アンロード
    if veh.JBeam ~= 'dashplate_mathkuro' then
      if mode == 'vehicle' then
        veh:queueLuaCommand("extensions.load('mathkuro_dashplateScanner')")
      else
        veh:queueLuaCommand("extensions.unload('mathkuro_dashplateScanner')")
      end
    else
      -- 全dashplateにupdateの有効/無効を通知
      veh:queueLuaCommand("controller.getController('executeFunction').applyScanMode('" .. mode .. "')")
    end
  end
  log('I', logTag, 'Scan mode changed to: ' .. mode)
end

-- 性能測定（GE側: executeOnVehicle）
local PERF_LOG_INTERVAL_SEC = 10
local perfGeVlua = { totalTime = 0.0, callCount = 0, lastLogTime = 0.0 }

local function logPerfStats()
  local s = perfGeVlua
  if s.callCount == 0 then return end
  local now = os.clock()
  if now - s.lastLogTime < PERF_LOG_INTERVAL_SEC then return end
  log("I", logTag, string.format(
    "[PERF][GE-vlua] %d calls in %.1fs | avg %.4f ms/call | total %.4f ms",
    s.callCount, PERF_LOG_INTERVAL_SEC, s.totalTime / s.callCount * 1000, s.totalTime * 1000))
  s.totalTime = 0.0
  s.callCount = 0
  s.lastLogTime = now
end

-- ref: lua\ge\extensions\core\funstuff.lua
local function paintRandomColor(veh, params)
  local changeColorFrequency = params and params.dashplateChangeColorFrequency or 50
  if math.random(1, 100) > changeColorFrequency then return end
  if not veh then return end
  local modelInfo = core_vehicles.getModel(veh.JBeam)
  if not modelInfo then return end
  local paints = tableKeys(tableValuesAsLookupDict(modelInfo.model.paints or {}))
  local paint1 = paints[math.random(1, #paints)]
  local paint2 = paints[math.random(1, #paints)]
  local paint3 = paints[math.random(1, #paints)]
  local paintData = {
    createVehiclePaint({x=paint1.baseColor[1], y=paint1.baseColor[2], z=paint1.baseColor[3], w=paint1.baseColor[4]}, {paint1.metallic, paint1.roughness, paint1.clearcoat, paint1.clearcoatRoughness}),
    createVehiclePaint({x=paint2.baseColor[1], y=paint2.baseColor[2], z=paint2.baseColor[3], w=paint2.baseColor[4]}, {paint2.metallic, paint2.roughness, paint2.clearcoat, paint2.clearcoatRoughness}),
    createVehiclePaint({x=paint3.baseColor[1], y=paint3.baseColor[2], z=paint3.baseColor[3], w=paint3.baseColor[4]}, {paint3.metallic, paint3.roughness, paint3.clearcoat, paint3.clearcoatRoughness}),
  }
  veh.color          = ColorF(paintData[1].baseColor[1], paintData[1].baseColor[2], paintData[1].baseColor[3], paintData[1].baseColor[4]):asLinear4F()
  veh.colorPalette0  = ColorF(paintData[2].baseColor[1], paintData[2].baseColor[2], paintData[2].baseColor[3], paintData[2].baseColor[4]):asLinear4F()
  veh.colorPalette1  = ColorF(paintData[3].baseColor[1], paintData[3].baseColor[2], paintData[3].baseColor[3], paintData[3].baseColor[4]):asLinear4F()
  veh:setMetallicPaintData(paintData)
end

local function execRepair(veh, params)
  params = params or {}
  local targetVid = veh:getID()
  local intervalSec = params.dashplateRepairIntervalSec or 5
  if os.time() - (repairState[targetVid] or 0) >= intervalSec then
    veh:queueLuaCommand('recovery.startRecovering()')
    veh:queueLuaCommand('recovery.stopRecovering()')
    veh:resetBrokenFlexMesh()
    repairState[targetVid] = os.time()
  end
end

local function registerTeleportGate(dashplateVid, gateNumber, role)
  role = role or 0
  teleportGateRoles[dashplateVid] = role
  if gateNumber == 0 then return end
  if role == 1 then return end  -- 入口専用はテレポート先候補リストに登録しない
  if not teleportGateRegistry[gateNumber] then teleportGateRegistry[gateNumber] = {} end
  for _, vid in ipairs(teleportGateRegistry[gateNumber]) do
    if vid == dashplateVid then return end
  end
  table.insert(teleportGateRegistry[gateNumber], dashplateVid)
end

local function getRandomSpawnPosRot()
  local currentLevel = getCurrentLevelIdentifier()
  if not currentLevel then return nil, nil end
  local levelInfo = nil
  for _, info in ipairs(core_levels.getList()) do
    if string.lower(info.levelName) == string.lower(currentLevel) then levelInfo = info end
  end
  if not levelInfo or not levelInfo.spawnPoints then return nil, nil end
  local randomSpawnPoint = levelInfo.spawnPoints[math.random(1, #levelInfo.spawnPoints)]
  if not randomSpawnPoint or not randomSpawnPoint.objectname then return nil, nil end
  local startPos = scenetree.findObject(randomSpawnPoint.objectname):getPosition()
  local spawnData = { pos = vec3(), dir = vec3() }
  local valid = false
  spawnData, valid = gameplay_traffic_trafficUtils.findSafeSpawnPoint(startPos, nil, 4000, nil, nil, {usePrivateRoads = false, minDrivability = 0.6})
  if valid then
    local normal = map.surfaceNormal(spawnData.pos, 1)
    local rot = quatFromDir(vec3(0,1,0):rotated(quatFromDir(spawnData.dir, normal)), normal)
    return spawnData.pos, rot
  end
end

local function execTeleport(veh, params)
  params = params or {}
  -- 出口専用のdashplateは発動しない
  if teleportGateRoles[params.dashplateVid] == 2 then return end

  local targetVid = veh:getID()
  local currentTime = os.time()
  if teleportCooldowns[targetVid] and currentTime < teleportCooldowns[targetVid] then return end

  local dashplateVid = params.dashplateVid
  local gateNumber = params.dashplateTeleportGateNumber or 0
  local destPos, destRot = nil, nil

  if gateNumber > 0 then
    local gateList = teleportGateRegistry[gateNumber]
    if gateList and #gateList > 0 then
      local candidates = {}
      for _, vid in ipairs(gateList) do
        if vid ~= dashplateVid and be:getObjectByID(vid) then table.insert(candidates, vid) end
      end
      if #candidates > 0 then
        local destVid = candidates[math.random(1, #candidates)]
        local destObj = be:getObjectByID(destVid)
        log("D", logTag, string.format("Teleport: vehicle %d to gate %d (dest vid %d)", targetVid, gateNumber, destVid))
        if destObj then
          destPos = destObj:getPosition()
          destRot = quat(0, 0, 1, 0) * destObj:getRotation()
        end
      end
    end
  end

  if not destPos then destPos, destRot = getRandomSpawnPosRot() end
  if not destPos then
    log("W", logTag, "Teleport: no destination found for vehicle " .. targetVid)
    return
  end

  spawn.safeTeleport(veh, destPos, destRot)
  teleportCooldowns[targetVid] = currentTime + TELEPORT_COOLDOWN_SEC
end

-- GE専用Gimmick（teleport, paintRandomColor, repair, openLatches）のディスパッチテーブル
local execFunctions = {
  teleport        = function(veh, params) execTeleport(veh, params) end,
  paintRandomColor = function(veh, params) paintRandomColor(veh, params) end,
  repair          = function(veh, params) execRepair(veh, params) end,
  openLatches     = function(veh) core_vehicleBridge.executeAction(veh, 'latchesOpen') end,
}

-- vlua方式: VLUAがスキャン済みの対象車両1台に対してGE専用処理を行う
local function executeOnVehicle(targetVid, functionName, params)
  --local t0 = os.clock()
  local veh = be:getObjectByID(targetVid)
  if veh then
    local func = execFunctions[functionName]
    if func then func(veh, params) end
  end
  --[[
  local s = perfGeVlua
  s.totalTime = s.totalTime + (os.clock() - t0)
  s.callCount = s.callCount + 1
  ]]--
end

local function showMessage(titleStr, valueStr)
  guihooks.message(string.format("%s: %s", titleStr, valueStr), 1, "dashplateMessage")
end

local function onUpdate()
  -- テレポートクールダウンの期限切れエントリをクリア（メモリリーク防止）
  local currentTime = os.time()
  for targetVid, cooldownEnd in pairs(teleportCooldowns) do
    if currentTime >= cooldownEnd then teleportCooldowns[targetVid] = nil end
  end
  -- logPerfStats()
end

local function onVehicleDestroyed(vid)
  repairState[vid] = nil
  teleportCooldowns[vid] = nil
  teleportGateRoles[vid] = nil
  for gateNumber, list in pairs(teleportGateRegistry) do
    for i = #list, 1, -1 do
      if list[i] == vid then table.remove(list, i) end
    end
    if #list == 0 then teleportGateRegistry[gateNumber] = nil end
  end
  if dashplateRegistry[vid] then
    dashplateRegistry[vid] = nil
    sendRegistryToMailbox()
  end
end

M.onUpdate = onUpdate
M.onVehicleDestroyed = onVehicleDestroyed
M.onVehicleSpawned = onVehicleSpawned
M.executeOnVehicle = executeOnVehicle
M.showMessage = showMessage
M.registerTeleportGate = registerTeleportGate
M.registerDashplate = registerDashplate
M.getDashplateRegistry = getDashplateRegistry
M.getScanMode = getScanMode
M.setScanMode = setScanMode
M.onExtensionLoaded = onExtensionLoaded


-- Backward compatibility
local THRUSTERS_VELOCITY = 50
local VELOCITY_RAMP_SEC = 0.05

local function execDashplate(dashplateVid, powerLevel, directionVector)
  local thrustersVelocity = powerLevel or THRUSTERS_VELOCITY
  local dashplatePos = be:getObjectByID(dashplateVid):getPosition()
  -- dash方向の速度成分だけを置き換え、上下動・横方向の成分は現在値を維持する
  local commandFormat =
    'local d=%s local v=obj:getVelocity() thrusters.applyVelocity(v-d*v:dot(d)+d*%.4f,%.4f)'
  for vid, veh in activeVehiclesIterator() do
    if vid ~= dashplateVid then
      if veh:getPosition():distance(dashplatePos) < DASHFIELD_DISTANCE then
        local dirExpr = directionVector == nil
          and 'obj:getDirectionVector():normalized()'
          or serialize(vec3(directionVector):normalized())
        veh:queueLuaCommand(string.format(commandFormat, dirExpr, thrustersVelocity, VELOCITY_RAMP_SEC))
      end
    end
  end
end

local function showPowerLevelMessage(level)
  local velocity, unit = translateVelocity(level, true)
  guihooks.message(string.format("Power Level: %d %s", velocity, unit), 1, "dashplatePowerLevel")
end

local function showDirectionModeMessage(directionMode)
  guihooks.message(string.format("Direction Mode: %s", directionMode), 1, "dashplateDirectionMode")
end

M.execDashplate = execDashplate
M.showPowerLevelMessage = showPowerLevelMessage
M.showDirectionModeMessage = showDirectionModeMessage

return M
