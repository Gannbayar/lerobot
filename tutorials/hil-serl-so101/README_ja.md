# SO-101 で学ぶ HIL-SERL

LeRobot の HIL-SERL（Human-in-the-Loop Sample-Efficient Reinforcement Learning）を、SO-101 実機で学ぶための日本語ガイドです。少量の人間のデモで報酬分類器を学習し、実機での強化学習中に人が介入して方策を導く流れを説明します。

## 対象

- LeRobot の HIL-SERL の流れを理解したい人
- SO-101 follower、カメラ、対応する teleoperator を用意できる人
- Python 環境やロボットのポート・カメラ設定を自分の機材に合わせられる人

実機を動かす前に、[LeRobot HIL-SERL 実機ガイド](https://github.com/huggingface/lerobot/blob/main/docs/source/hilserl.mdx) と [シミュレーションガイド](https://github.com/huggingface/lerobot/blob/main/docs/source/hilserl_sim.mdx) を読んでください。初めて試す場合はシミュレーションから始めてください。依存関係、コマンド、設定項目はLeRobot本体のバージョンに合わせて公式ガイドを参照してください。

## 学習の流れ

1. **環境を準備する** — LeRobot を HIL-SERL extra 付きでインストールし、カメラ、ロボット、teleoperator を個別に接続確認します。
2. **デモを集める** — タスクの成功・失敗例を teleoperation で記録します。報酬分類器用データでは、成功状態の例を十分に含めます。
3. **報酬分類器を学習する** — カメラ画像から成功状態を判定する分類器を学習し、画像で判定結果を確認します。
4. **actor と learner を起動する** — learner を先に起動し、同じ学習設定を使う actor を別プロセスで起動します。
5. **人が介入しながら学習する** — 方策が失敗しそうなとき teleoperator へ操作を切り替え、安全にタスクを完了させます。介入回数と成功率を記録します。

## 環境の設定

ローカル設定では、機材に合わせて次の値を指定します。公開する設定例には実ポート名や個人のファイルパスを書かないでください。

- follower / leader のデバイスパス
- カメラ名とデバイス番号
- URDF の場所、エンドエフェクタの座標範囲
- データセットと報酬分類器の Hub ID
- GPU / CPU の選択

Hub へのアップロードは公開先とデータ内容を確認してから有効にしてください。収録データや学習済み重みはこのガイドに含めず、別途配布する場合は取得先とライセンスを記載してください。

## 実機の安全

- 最初は低速・小さい動作範囲で確認し、ロボットをすぐ停止できる位置にいてください。
- 作業空間から人や壊れやすい物を離してください。
- 緊急停止の方法を確認してから actor を起動してください。
- actor と learner の設定、カメラ入力、介入デバイスを確認せずに長時間運転しないでください。

## GitHub で教材を共有するとき

LeRobot 本体のコード変更は [LeRobot の fork](https://github.com/huggingface/lerobot) 上で管理してください。個人用モデル重み、収録データ、実機ログ、ローカル設定、Hub の認証情報、別リポジトリの .git ディレクトリは教材リポジトリに含めないでください。SO-ARM100 の CAD 資産を再配布する場合は、[元リポジトリ](https://github.com/TheRobotStudio/SO-ARM100) のライセンスと帰属表示も維持してください。

## 関連資料

- [LeRobot HIL-SERL 実機ガイド](https://github.com/huggingface/lerobot/blob/main/docs/source/hilserl.mdx)
- [LeRobot HIL-SERL シミュレーションガイド](https://github.com/huggingface/lerobot/blob/main/docs/source/hilserl_sim.mdx)
- [HIL-SERL の元論文](https://arxiv.org/abs/2309.02709)
- [SO-ARM100 / SO-101 の組み立て資料](https://github.com/TheRobotStudio/SO-ARM100)
