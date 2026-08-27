/* global bngApi */
angular
.module('beamng.apps')
.controller('AppCtrl', function ($scope, $timeout) {
  // ---- 定数 ----
  // randomFunctionsのキー から画像ファイル名への対応マッピング
  // Luaのrandomfunctionsキーから"dashplateRandom"を削除したもの
  const FUNCTION_TO_IMAGE_MAP = {
    // Luaの randomFunctions key: dashplateRandom* → 削除後の名前
    'BreakHinges': 'break_hinges',
    'BreakRandom': 'break_random',
    'Dash': [
      'dash_100KMH',
      'dash_200KMH',
      'dash_300KMH',
      'dash_500KMH',
      'dash_1000KMH'
    ],
    'DashJump': 'dash_jump',
    'DashOneWay': 'dash_one_way',
    'DashReverse': 'dash_reverse',
    'DashStop': 'dash_stop',
    'DashTurnLeft': 'dash_turn_left',
    'DashTurnRight': 'dash_turn_right',
    'DeflateTires': 'deflate_tire',
    'Explode': 'explode',
    'Ignite': 'ignite',
    'Open': 'open',
    'Paint': 'paint',
    'Spin': 'spin',
    'Tornado': 'tornado',
    'Flip': 'side_flip',
    'FrontFlip': 'front_flip',
    'ToggleLights': 'toggle_light',
    'Repair': 'repair',
    'Slingshot': 'sling_shot',
    'Fireworks': 'fireworks',
    'Teleport': 'teleport',
    'ScaleSpeed': 'scale_speed',
    'Extinguish': 'extinguish'
  };

  const IMAGE_BASE_PATH = '/vehicles/dashplate_mathkuro/dashplate_fc_';
  const IMAGE_EXTENSION = '.jpg';

  // ---- UI変数 ----
  $scope.settings = {
    uiEnabled: true,
    hideImageOnEmpty: false,
    targetVid: null // 追加: 対象車両IDを保存する変数
  };

  $scope.currentImagePath = '';
  $scope.currentFunctionName = '';
  $scope.currentFunctionLabel = '';

  /**
   * Luaのキーから関数名に変換
   * @param {string} luaKey - LuaのrandomFunctionsキー（例: 'dashplateRandomBreakHinges'）
   * @returns {string} 関数名（例: 'BreakHinges'）
   */
  function extractFunctionNameFromKey(luaKey) {
    if (!luaKey) return '';
    
    // "dashplateRandom"プレフィックスを削除
    if (luaKey.startsWith('dashplateRandom')) {
      return luaKey.substring('dashplateRandom'.length);
    }
    
    return luaKey;
  }

  /**
   * 関数名からイメージパスを生成
   * @param {string} functionName - 関数名（例: 'BreakHinges', 'Dash'など）
   * @param {object} params - パラメータオブジェクト（speed情報などに使用）
   * @returns {string} イメージファイルのパス
   */
  function getImagePathFromFunctionName(functionName, params) {
    if (!functionName) {
      return '';
    }

    let imageName = FUNCTION_TO_IMAGE_MAP[functionName];
    if (!imageName) {
      console.warn('Unknown function: ' + functionName);
      return '';
    }

    // dashのように複数のバリエーションがある場合、パラメータから選択
    if (Array.isArray(imageName)) {
      imageName = selectImageVariant(functionName, imageName, params);
    }

    return IMAGE_BASE_PATH + imageName + IMAGE_EXTENSION;
  }

  /**
   * ダッシュ関数のバリエーション画像を選択
   * @param {string} functionName - 関数名
   * @param {array} variants - バリエーション配列
   * @param {object} params - パラメータ
   * @returns {string} 選択された画像名
   */
  function selectImageVariant(functionName, variants, params) {
    // dashの場合、speed情報があればそれに基づいて選択
    if (functionName === 'Dash' && params && params.dashplateSpeedKMH) {
      const speed = params.dashplateSpeedKMH;
      if (speed <= 100) return 'dash_100KMH';
      if (speed <= 200) return 'dash_200KMH';
      if (speed <= 300) return 'dash_300KMH';
      if (speed <= 500) return 'dash_500KMH';
      return 'dash_1000KMH';
    }

    // デフォルトは最初のバリエーション
    return variants[0];
  }

  /**
   * 関数名をラベル表示用にフォーマッティング
   * @param {string} functionName - 関数名
   * @returns {string} ラベル用フォーマット
   */
  function formatFunctionLabel(functionName) {
    if (!functionName) return '';

    // PascalCaseをスペース区切りに変換して小文字に
    const formatted = functionName
      .replace(/([A-Z])/g, ' $1')
      .replace(/^[ ]/, '')
      .toLowerCase();

    return formatted;
  }

  // ---- イベント駆動UIアップデート ----
  let playerVehicleId = null;
  let clearTimer = null;

  // 初期化時にプレイヤー車両IDを取得
  bngApi.engineLua('be:getPlayerVehicleID(0)', function (vid) {
    playerVehicleId = vid;
  });

  // 車両切り替え時にプレイヤー車両IDを更新
  $scope.$on('VehicleFocusChanged', function (event, data) {
    console.log('VehicleFocusChanged event received, updating playerVehicleID to', data.id);
    playerVehicleId = data.id;
  });

  function clearCurrentFunction() {
    $scope.currentFunctionName = '';
    $scope.currentFunctionLabel = '';
    $scope.currentImagePath = '';
  }

  $scope.$on('mathkuroDashplateCurrentFunction', function (event, data) {
    if (!data || !data.functionName) return;
    // 自分が影響を受けた車、または自分がdashplate本体の場合のみ表示
    if (data.targetVid !== playerVehicleId && data.dashplateVid !== playerVehicleId) return;

    const functionName = extractFunctionNameFromKey(data.functionName);
    $scope.currentFunctionName = data.functionName;
    $scope.currentFunctionLabel = formatFunctionLabel(functionName);
    $scope.currentImagePath = getImagePathFromFunctionName(functionName, data.params);

    if (clearTimer) {
      $timeout.cancel(clearTimer);
    }
    clearTimer = $timeout(clearCurrentFunction, 3000);
  });

  $scope.$on('$destroy', function () {
    if (clearTimer) {
      $timeout.cancel(clearTimer);
    }
  });
})
.directive('dashplateMathkuro', [function () {
  return {
    templateUrl: '/ui/modules/apps/dashplateMathkuro/app.html',
    replace: true,
    restrict: 'EA',
    link: function (scope, element, attrs) {
      'use strict';
    }
  }
}]);
