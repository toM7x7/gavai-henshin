export const EXHIBITION_OPERATOR_COPY = Object.freeze({
  state: {
    pending: {
      label: "準備中",
      colorGuide: "黄: 入力待ち、読み込み中、またはスタッフ確認待ちです。",
    },
    queued: {
      label: "準備中",
      colorGuide: "黄: 生成や読み込みの順番待ちです。来場者にはそのまま待ってもらいます。",
    },
    running: {
      label: "認識中",
      colorGuide: "紫: 音声、装着、表面処理を確認中です。途中操作は止めてください。",
    },
    complete: {
      label: "生成完了",
      colorGuide: "青: Web生成またはQuest装着が完了し、次の案内へ進めます。",
    },
    ready: {
      label: "準備OK",
      colorGuide: "青: 呼び出しや表示に必要な準備がそろっています。",
    },
    ok: {
      label: "準備OK",
      colorGuide: "青: 呼び出しや表示に必要な準備がそろっています。",
    },
    error: {
      label: "要確認",
      colorGuide: "赤: コード、マイク、API、またはモデル読込をスタッフが確認します。",
    },
    warning: {
      label: "要確認",
      colorGuide: "黄: 展示は続行できますが、モデル納品やP1確認では止めて扱います。",
    },
    planned: {
      label: "未完了",
      colorGuide: "黄: 展示確認は可能ですが、納品品質としては追加確認が必要です。",
    },
    idle: {
      label: "待機中",
      colorGuide: "黄: 操作待ちです。次の案内を確認してください。",
    },
  },
  forge: {
    statusIdle: "入力待機中",
    statusHelpIdle: "黄: 来場者の入力待ちです。名前、身長、イメージを確認してください。",
    submit: "生成してコード発行",
    submitting: "生成条件を送信中...",
    assembling: "プレビューを組み立て中...",
    questPreparing: "Questリンクを準備中...",
    complete: "生成完了。4桁コードをQuestに入力してください。",
  },
  quest: {
    hudLabel: "Quest変身デモ操作",
    sceneLabel: "Quest没入シーン",
    routeLabel: "変身体験ルート状態",
    recallLabel: "Questスーツ呼び出し",
    readoutLabel: "セッション状態",
    statusReady: "Quest 3 VR準備OK。4桁コードを呼び出し、音声合図で変身します。",
    operatorHelpReady: "黄: 待機中です。4桁コード、マイク、VR開始の順に確認してください。",
    operatorHelpListening: "紫: 音声を認識中です。合図の後だけ発声してもらいます。",
    operatorHelpComplete: "青: 生成完了です。鏡または記録再生へ案内できます。",
    operatorHelpError: "赤: スタッフ確認が必要です。コード、マイク、API接続を見てください。",
    sessionWaiting: "セッション: 待機",
    triggerWaiting: "音声: 待機",
    equipWaiting: "変身: 待機",
  },
});

export function operatorStateCopy(state) {
  return EXHIBITION_OPERATOR_COPY.state[state] || EXHIBITION_OPERATOR_COPY.state.pending;
}

export function operatorStateLabel(state) {
  return operatorStateCopy(state).label;
}

export function operatorStateColorGuide(state) {
  return operatorStateCopy(state).colorGuide;
}
