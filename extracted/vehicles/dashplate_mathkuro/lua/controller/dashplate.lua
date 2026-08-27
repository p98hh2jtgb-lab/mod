-- This Source Code Form is subject to the terms of the bCDDL, v. 1.1.
-- If a copy of the bCDDL was not distributed with this
-- file, You can obtain one at http://beamng.com/bCDDL-1.1.txt

-- Thanks to CarlosAir for turning my lua into a controller, Diamondback for optimizing it. And byt optimizing I mean literally rewriting it to work properly,
---and thanks to Dummiesman and Chris for lua help

local M = {}
--Mandatory controller parameters
M.type = "main"
M.relevantDevice = nil
M.engineInfo = {}
M.gearboxInfo = {isReverse = false}
M.fireEngineTemperature = 0
M.throttle = 0
M.brake = 0
M.clutchRatio = 0

-- 加速の方向を指定するモード
-- "vehicle": 車両の方向
-- "plate": DashPlateの方向
local dashDirectionMode = "vehicle"

local platePowerLevel = 50

local function setPlatePowerLevel(level)
  platePowerLevel = level
  obj:queueGameEngineLua("mathkuro_dashplate.showPowerLevelMessage(" .. platePowerLevel .. ")")
  electrics.values.dashplatePowerLevel = platePowerLevel
end

local function changePlatePowerLevel(value)
  setPlatePowerLevel(platePowerLevel + value)
end

local function toggleDirectionMode()
  if dashDirectionMode == "vehicle" then
    dashDirectionMode = "plate"
  else
    dashDirectionMode = "vehicle"
  end

  obj:queueGameEngineLua("mathkuro_dashplate.showDirectionModeMessage('" .. dashDirectionMode .. "')")
  electrics.values.dashDirectionMode = dashDirectionMode
end

local function update(dt)
  if electrics.values.dashDirectionMode == "plate" then
    local vec = obj:getDirectionVector()
    obj:queueGameEngineLua("mathkuro_dashplate.execDashplate(" .. obj:getID() .. ", " .. electrics.values.dashplatePowerLevel .. ", " .. serialize(vec) .. ")")
  else
    obj:queueGameEngineLua("mathkuro_dashplate.execDashplate(" .. obj:getID() .. ", " .. electrics.values.dashplatePowerLevel .. ", nil)")
  end
end

local function init()
  -- オンデマンドでロードしているため、v0.31適用のLUAロードの最適化を採用した方が良いかも？
  obj:queueGameEngineLua("extensions.unload('mathkuro_dashplate')")
  obj:queueGameEngineLua("extensions.loadAtRoot('lua/ge/extensions/mathkuro/dashplate', 'mathkuro')")

  electrics.values.dashplatePowerLevel = 0
  setPlatePowerLevel(platePowerLevel)

  obj:queueGameEngineLua("mathkuro_dashplate.showDirectionModeMessage('" .. dashDirectionMode .. "')")
  electrics.values.dashDirectionMode = dashDirectionMode
end

M.init = init
M.update = update
M.setPowerLevel = setPlatePowerLevel
M.changePowerLevel = changePlatePowerLevel
M.toggleDirectionMode = toggleDirectionMode

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
