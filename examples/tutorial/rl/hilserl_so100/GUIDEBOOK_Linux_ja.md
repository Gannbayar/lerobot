# Linux 実機 HIL-SERL ガイドブック（SO-100 / SO-101）

このガイドは、Linux PCにロボットを接続するところから、デモ収録、報酬分類器、HIL-SERL学習、実機評価までを順に進めるための手順書です。操作対象は SO-100 / SO-101 follower、PS4コントローラー、カメラ、NVIDIA GPU を想定しています。

> **重要:** `/dev/leader` と `/dev/follower` はこの環境で使うデバイス名です。Linux PCで同じ名前が作られているとは限りません。最初に実際のUSBポートを調べ、以後の設定をその値に合わせてください。作業範囲や速度は実機ごとに測定します。以下の数値例を実機にそのまま適用しないでください。

## 全体の順序

1. LinuxでUSBロボット、カメラ、PS4、GPUを確認
2. LeRobotをセットアップ
3. leader / followerをキャリブレーション
4. 実測した作業範囲で安全設定を作成
5. 成功・失敗ラベル付きデモを収録
6. データセットの画像範囲（ROI）を切り出す
7. 報酬分類器を学習して確認
8. learnerを起動し、actorを接続してHIL-SERLを学習
9. 保存したチェックポイントを区切りに実機の成功率・介入回数を評価

シミュレーションは実機 HIL-SERL を始める必須条件ではありません。LeRobot付属の `gym_hil` は Franka Panda 用です。このフォルダーのSO-101コーヒーシーンは配置やカメラの見た目を確認するもので、実機のカメラ入力や学習環境には接続されません。

## 1. Linux PCで接続を確認する

ロボットをUSB接続し、Linuxのデスクトップにログインしてターミナルを開きます。まだキャリブレーションや学習は開始しません。

```bash
cd /path/to/lerobot
python3 -m venv .venv   # 初回だけ
source .venv/bin/activate
python -m pip install -e ".[hilserl,gamepad,feetech]"

nvidia-smi -L
lerobot-find-port
lerobot-find-cameras opencv
```

`/path/to/lerobot` は実際のリポジトリの場所に置き換えます。`lerobot-find-port` は案内に従ってUSB機器を1台ずつ確認し、leader / follower のポート名をメモします。例: `/dev/ttyACM0`、`/dev/ttyUSB0`。カメラ探索では使うカメラの番号、解像度、FPSを控えます。PS4は最初はUSB接続にします。

以後のコマンドで `/dev/leader`、`/dev/follower` と記載した箇所は、検出したポートに置き換えてください。毎回同じポート名で扱いたい場合はudevルールでシンボリックリンクを作れますが、USBの識別情報を確認してから設定します。

GPUが2枚見える場合は `nvidia-smi -L` に2台表示されます。最初の報酬分類器とlearnerはGPU 0（通常 `cuda:0`）で動かし、GPU 1は初回動作確認では使わなくて構いません。

## 2. leader / followerをキャリブレーションする

ロボットを動かせる状態にし、周囲の人や物を離します。各アームを安全な中間姿勢に置き、まずleader、次にfollowerを別々に実行します。

```bash
python -m src.lerobot.scripts.lerobot_calibrate \
  --teleop.type=so100_leader \
  --teleop.port=/dev/leader \
  --teleop.id=gray_leader
```

```bash
python -m src.lerobot.scripts.lerobot_calibrate \
  --robot.type=so100_follower \
  --robot.port=/dev/follower \
  --robot.id=white_follower
```

検出したデバイスパスに合わせて `port` を変更します。キャリブレーション画面の指示に従い、関節を無理のない範囲で動かします。保存したID（`gray_leader` / `white_follower`）は後の設定でも同じ値を使います。

## 3. URDFと安全な作業範囲を設定する

SO-ARM100公式リポジトリの `Simulation/SO101/so101_new_calib.urdf` を取得し、絶対パスを控えます。LeRobotの公式手順にある `lerobot-find-joint-limits` を使い、leaderをゆっくり動かしながらタスクを安全に行えるfollowerの範囲を測ります。

```bash
lerobot-find-joint-limits \
  --robot.type=so100_follower \
  --robot.port=/dev/follower \
  --robot.id=white_follower \
  --teleop.type=so100_leader \
  --teleop.port=/dev/leader \
  --teleop.id=gray_leader \
  --urdf_path=/path/to/SO-ARM100/Simulation/SO101/so101_new_calib.urdf \
  --target_frame_name=gripper \
  --teleop_time_s=30 \
  --warmup_time_s=5
```

表示されたエンドエフェクタの最小・最大値をメモし、収録設定の `end_effector_bounds.min/max` に入力します。限界まで関節を動かさず、カップや机に当たらない余裕を残します。URDFパス、ポート、ID、カメラ番号、作業範囲を記録しておきます。

## 4. 成功・失敗デモを収録する

詳細なJSON例は [共通ガイドの実機収録設定](README_ja.md#4-成功失敗ラベル付きのデータを記録する)を使います。例を `examples/tutorial/rl/hilserl_so100/reward_record.json` に保存し、少なくとも次の値を手元の機材に合わせます。

- `env.robot.port`, `env.robot.id`: followerのポートと `white_follower`
- `env.robot.cameras.front.index_or_path`: 検出した実カメラ番号
- `env.processor.inverse_kinematics.urdf_path`: 実際のURDFパス
- `end_effector_bounds.min/max`: 直前に測った値
- `dataset.repo_id/root`: ローカル保存先。Hubへ上げない間は `push_to_hub: false`
- `env.processor.reset.terminate_on_success`: 収録中は `false`

```bash
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/reward_record.json
```

課題はまず5～10秒で終わる短い動作にします。コーヒーカップと砂糖ブロックなら「砂糖ブロックをつかみ、カップの中へ入れる」など、カメラ画像で成功を判定できる条件を決めます。

PS4操作ではスティックとL2/R2で直接操作します。タスク成功状態になったら **Triangle（△）** で成功ラベルを付け、成功姿勢や位置を少し変えて例を集めます。失敗した試行は **Cross（×）**、やり直しは **Square（□）** です。成功10・失敗10程度、成功状態のラベル付きフレームを100枚程度から始めるのは実務上の目安で、必須数ではありません。光、物体位置、カメラに写る姿勢を変えた例も含めます。

収録後、データが指定した `data/so100_reward_labels` などに保存されたことを確認します。収録データには人や周囲が映ることがあるため、公開・Hubアップロード前に内容と公開範囲を確認します。

## 5. 画像のROIを設定する

腕先、砂糖ブロック、カップを含み、関係のない背景をなるべく除くようにROIを選びます。

```bash
python -m lerobot.rl.crop_dataset_roi \
  --repo-id local/so100_reward_labels \
  --root data/so100_reward_labels \
  --task "pick up the sugar block and put it inside the cup"
```

画面で各カメラの範囲を選び、`c` で確定します。生成された `meta/crop_params.json` の各画像の `[top, left, height, width]` を控えます。後でactor / learner設定にも同じ値を入れます。出力先は通常 `local/so100_reward_labels_cropped_resized` と `data/so100_reward_labels_cropped_resized` です。

## 6. 報酬分類器を学習・確認する

詳細設定例は [共通ガイドの分類器設定](README_ja.md#6-報酬分類器を学習する)を参照し、`reward_classifier_train.json` として保存します。datasetはROI処理後のもの、カメラ名は `front`、入力shapeは `[3, 128, 128]`、GPUは `cuda` にします。

```bash
CUDA_VISIBLE_DEVICES=0 lerobot-train \
  --config_path examples/tutorial/rl/hilserl_so100/reward_classifier_train.json
```

出力モデルは通常 `outputs/so100_reward_classifier/checkpoints/last/pretrained_model` にあります。actor / learner設定で `env.processor.reward_classifier.pretrained_path` にその場所を指定します。

学習後は、学習に使わなかった成功・失敗エピソードも含めて画像を見直します。成功状態を失敗、失敗状態を成功と取り違える場合や、背景だけで判定している場合は、デモを追加してROIやラベルを見直し、再学習します。分類器の学習損失だけで実機上の成功判定が正しいとは判断しません。

## 7. actor / learner設定を作る

公式の [actor-learner設定例](https://huggingface.co/datasets/lerobot/config_examples/resolve/main/rl/train_config.json)をコピーし、`examples/tutorial/rl/hilserl_so100/train_hilserl.json` として保存します。JSON例と項目一覧は[共通ガイド](README_ja.md#7-actor--learner-用設定を作る)を参照してください。最低限、次を合わせます。

- ロボット種類 `so100_follower`、正しいポートとID、実カメラ設定
- `env.name: real_robot`、teleoperator `gamepad`、`control_mode: gamepad`
- 実測したURDFとエンドエフェクタ範囲
- 画像ROIと `[128, 128]` resize
- 報酬分類器の `pretrained_path`
- `terminate_on_success: true`（学習時）
- SO-100の6関節state、XYZの連続action、グリッパー3離散actionに合うpolicy特徴量
- `policy.device: cuda`、`policy.online_steps` と出力先
- Hub公開とW&Bを使わない間は `push_to_hub: false`、`wandb.enable: false`

actorとlearnerは**同じ設定ファイル**を使います。学習を再開するとき以外は、既存の `output_dir` を使い回さず新しいディレクトリを指定します。

## 8. HIL-SERLを起動して学習する

ロボットを安全な開始姿勢にし、緊急停止手段を確認します。ターミナルを2つ開き、仮想環境を両方で有効にします。

**ターミナル1: learner**

```bash
cd /path/to/lerobot
source .venv/bin/activate
python -m lerobot.rl.learner \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl.json
```

learnerのgRPCサーバー起動を確認したら、actorを開始します。

**ターミナル2: actor（実機を動かす）**

```bash
cd /path/to/lerobot
source .venv/bin/activate
python -m lerobot.rl.actor \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl.json
```

actorが動き始めたら、すぐそばで監視します。PS4の **R1を押している間は人が操作を引き継ぎ**、スティックとL2/R2で軌道を修正します。R1を離すと方策に戻ります。成功はTriangle、失敗はCrossで記録します。最初は介入を多めに行い、動作が安定したら減らします。

停止時は actor のターミナルで `Ctrl+C`、終了後に learner のターミナルで `Ctrl+C` を押します。learnerの `output_dir/checkpoints/` に保存されたcheckpointとログを確認します。`checkpoints/last` は最後に保存されたモデルへのリンクです。

## 9. 実機で評価する

このチェックアウトのHIL-SERL実機ループには、実機用の独立した「学習を止めて固定checkpointを自動評価する」コマンドが用意されていません。`src/lerobot/rl/eval_policy.py` はこの用途でそのまま使える状態ではないため、独立評価用コマンドとして案内しません。そこで、checkpointを保存した時点ごとに、同じ開始位置・同じ課題で試行記録を取り、**学習中の方策の進み具合**を比較します。これは完全に固定方策を測るベンチマークとは区別します。

### 評価の準備

1. 収録に使わなかった、別の配置・試行を評価用として残します。
2. 開始位置、物体位置、照明、成功条件を決め、全試行で同じ条件にします。
3. 最初の評価区間では安全担当者がすぐ介入できる状態を保ちます。
4. checkpointのパス、learnerのoptimization step、評価日時を記録します。

### 10試行ごとに記録する項目

| 項目 | 記録方法 |
| --- | --- |
| 成功数 / 成功率 | タスク条件を満たした試行を成功。成功数 ÷ 10 |
| 自律成功率 | 人のR1介入なしで成功した数 ÷ 10 |
| 介入回数 | R1で引き継いだ回数。介入後に成功した試行も別記 |
| 完了時間 | 開始から成功または制限時間までの秒数 |
| 失敗理由 | 取り損ね、落下、カップ外、範囲端への接近など |
| 報酬判定の誤り | 成功を失敗、失敗を成功と判定した回数 |
| 安全事象 | 接触、異音、予期しない動作。発生したら評価を止めて原因を確認 |

例として、10試行中8回以上成功し、自律成功率が上がり、介入回数が減るかを進捗の目安にできます。この数値はこの教材での運用目安であり、公式HIL-SERLの合格基準ではありません。成功率だけでなく、安全事象や報酬誤判定も確認します。

```text
checkpoint: outputs/so100_hilserl/checkpoints/<保存されたcheckpointのstep>
条件: カップを固定位置、砂糖ブロックを開始マークに置く
試行: 10 / 成功: __ / 自律成功: __ / 介入回数: __
完了時間（秒）: __, __, __, ...
失敗・誤判定・安全事象:
```

評価中もactor / learnerを動かしている場合、方策が更新される可能性があります。checkpoint間の比較は「その学習区間での運用成績」として記録し、学習停止後の固定方策評価と混同しないでください。完全に固定したcheckpointだけを評価したい場合は、固定方策の実機評価ランナーを別途用意・検証する必要があります。

## よくある問題

- **ポートが開けない:** `lerobot-find-port` で再確認し、必要ならLinuxのシリアルデバイス権限とudev設定を確認します。
- **カメラ番号が違う:** `lerobot-find-cameras opencv` を再実行し、JSON内の `index_or_path` を更新します。
- **CUDAが使えない:** `nvidia-smi -L` と仮想環境内のPyTorch CUDA認識を確認します。オンライン学習をCPUで進める前にGPU環境を直します。
- **分類器が成功を誤判定する:** 成功・失敗ラベル、未使用の検証例、ROIを確認してデータを追加します。誤判定のまま実機学習を続けません。
- **actorがworkspace外へ行こうとする:** R1で即時介入し、停止してbounds、URDF、カメラ、座標系を見直します。
- **learnerに接続できない:** learnerを先に起動し、2つの設定が同じ `learner_host` / `learner_port` を使っているかを確認します。

## 関連資料

- [共通ガイド（PS4、設定JSON、収録操作）](README_ja.md)
- [Linuxシミュレーション・SO-101シーン](README_Linux_ja.md)
- [LeRobot公式 HIL-SERLガイド](https://huggingface.co/docs/lerobot/en/hilserl)
- [SO-ARM100 / SO-101公式モデル](https://github.com/TheRobotStudio/SO-ARM100)
