# SO-100 で学ぶ HIL-SERL

LeRobot の HIL-SERL（Human-in-the-Loop Sample-Efficient Reinforcement Learning）を、SO-100 実機で学ぶための教材入口です。HIL-SERL は、少量の人間のデモで報酬分類器を学習し、実機での強化学習中に人が介入して方策を導く手法です。

## 対象

- LeRobot の HIL-SERL の流れを理解したい人
- SO-100 leader / follower、カメラ、PS4 コントローラーを用意できる人
- Python 環境やロボットのポート・カメラ設定を自分の機材に合わせられる人

実機を動かす前に、公式の [HIL-SERL 実機ガイド](../../../../docs/source/hilserl.mdx) と [シミュレーションガイド](../../../../docs/source/hilserl_sim.mdx) を読んでください。初めて試す場合はシミュレーションから始めてください。

## 学習の流れ

1. **環境を準備する** — LeRobot を HIL-SERL extra 付きでインストールし、カメラ、ロボット、teleoperator を個別に接続確認します。
2. **デモを集める** — タスクの成功・失敗例を teleoperation で記録します。報酬分類器用データを作るときは、成功状態の例が十分に含まれるようにします。
3. **報酬分類器を学習する** — カメラ画像から成功状態を判定する分類器を学習し、少数の画像で判定結果を確認します。
4. **actor と learner を起動する** — learner を先に起動し、同じ学習設定を使う actor を別プロセスで起動します。
5. **人が介入しながら学習する** — 方策が失敗しそうなときに teleoperator へ操作を切り替え、安全にタスクを完了させます。介入が減っているか、成功率とともに記録します。

このREADMEは SO-100 leader / follower と PS4 を使う場合の手順です。別のロボットや LeRobot の版を使う場合は、[公式 HIL-SERL 実機ガイド](https://huggingface.co/docs/lerobot/en/hilserl)と設定例も確認してください。

## 実機をつなぐ前にシミュレーションする

シミュレーションには目的の異なる2つの方法があります。**HIL-SERL の操作手順を練習する環境は Franka Panda** です。SO-101 の形を確認するだけなら、公式 MuJoCo モデルを別ビューアで開けます。後者はロボットの見た目を確認する方法で、HIL-SERLのタスク環境ではありません。

### SO-101 のモデルを MuJoCo で表示する（macOS）

公式の [SO-ARM100 リポジトリ](https://github.com/TheRobotStudio/SO-ARM100)には SO-101 の MuJoCo モデルがあります。以下はモデルのシーンを表示する手順です。すでに `SO-ARM100` をダウンロード済みなら `git clone` は飛ばし、その場所を最後のコマンドに指定してください。

```bash
cd ~
git clone --depth 1 https://github.com/TheRobotStudio/SO-ARM100.git
cd /Volumes/ssd_sata/lerobot
source .venv/bin/activate
python -m mujoco.viewer --mjcf="$HOME/SO-ARM100/Simulation/SO101/scene.xml"
```

MuJoCo のシーンに SO-101 のモデルが表示されます。これは通常の MuJoCo viewer を起動するため `python` を使います。`mjpython` が必要なのは、HIL-SERL が使う `launch_passive` を macOS から起動するときです。このビューアには HIL-SERL の Panda 用キーボード操作や、学習・データ収集機能はありません。LeIsaac / Isaac Lab には SO-101 のタスク環境もありますが、公式セットアップは CUDA 対応環境を使います。M2 Mac で動かす場合は公式の[クラウドシミュレーション案内](https://github.com/huggingface/lerobot/blob/main/docs/source/envhub_leisaac.mdx)を確認してください。

### HIL-SERL の操作をシミュレーションする

LeRobot の `gym_hil` シミュレーターは MuJoCo 上の **Franka Panda** です。HIL-SERL の操作の流れは試せますが、SO-101 と同じ関節や動きにはなりません。オンライン学習は公式ガイドが NVIDIA GPU を必要環境としているため、M2 Mac では操作の確認までにしてください。

リポジトリのルートで依存関係を入れます。前の節で LeRobot 用 `.venv` を作っていれば、それを有効にして使います。macOS で MuJoCo の画面を開くときは、通常の `python` ではなく MuJoCo 付属の `mjpython` を使います。これは MuJoCo の `launch_passive` が macOS では `mjpython` 起動を要求するためです（[MuJoCo 公式ドキュメント](https://github.com/google-deepmind/mujoco/blob/main/doc/python.rst)）。

```bash
cd /path/to/lerobot
source .venv/bin/activate
pip install -e ".[hilserl]"
```

設定ファイル `examples/tutorial/rl/hilserl_so100/gym_hil_sim.json` を使います。`robot` と `teleop` は不要です。シミュレーター内蔵のキーボード操作を使い、データセットは作らず、学習もしない表示・操作確認用の設定です。

macOS:

```bash
mjpython -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

Linux:

```bash
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

ウィンドウが開いたら、矢印キーと修飾キーは押している間だけ動きます。Enter と Esc は現在のエピソードをそれぞれ成功・失敗として終了します。Esc はアプリ終了ではありません。シミュレーター自体を終了するときはターミナルで `Ctrl+C` を押します。

| キー | 動作 |
| --- | --- |
| ↑ / ↓ | X 軸を + / - 方向へ動かす |
| ← / → | Y 軸を + / - 方向へ動かす |
| 左 Shift / 右 Shift | Z 軸を - / + 方向へ動かす |
| 右 Ctrl / 左 Ctrl | グリッパーを開く / 閉じる |
| Enter / Esc | エピソードを成功 / 失敗として終了 |
| Space | 介入モードを切り替える |
| R | エピソードを記録し直す |

シミュレーターは Franka Panda 用なので、実ロボットのID `gray_leader` / `white_follower` はここでは使いません。PS4で試す場合は設定の `task` を `PandaPickCubeGamepad-v0` に切り替えます。ゲームパッド操作は gym-hil 側のマッピングが使われ、LeRobot 実機用 PS4 マッピングとは別です。

### PS4（DualShock 4）の操作

| コントローラー | 操作 | 動作 |
| --- | --- | --- |
| 左スティック上 / 下 | 倒す | X 軸を + / - 方向へ動かす |
| 左スティック左 / 右 | 倒す | Y 軸を + / - 方向へ動かす |
| 右スティック上 / 下 | 倒す | Z 軸を + / - 方向へ動かす |
| L2 | 押す | グリッパーを閉じる |
| R2 | 押す | グリッパーを開く |
| R1 | 押している間 | 方策を中断して人が操作する（介入） |
| Triangle（△） | 1 回押す | 成功ラベルを付ける |
| Cross（×） | 1 回押す | 失敗としてエピソードを終了する |
| Square（□） | 1 回押す | 現在のエピソードを破棄して記録し直す |

スティックを倒す量に応じて移動指令が変わります。中央付近の小さな入力は無視されます。グリッパー操作を使うには、teleoperator と `env.processor.gripper` の両方で `use_gripper: true` にしてください。L2 と R2 を同時に押した場合、グリッパーはその場で停止します。

### 実機で HIL-SERL を始める順番（SO-100 follower + PS4）

以下は **SO-100 leader (`/dev/leader`, ID `gray_leader`)、SO-100 follower (`/dev/follower`, ID `white_follower`)、前方カメラ1台、PS4、Linux + NVIDIA GPU** の構成例です。カメラ番号、URDF、作業範囲は機材に合わせてください。LeRobot の[公式 HIL-SERL 実機ガイド](https://huggingface.co/docs/lerobot/en/hilserl)にも全体の構成があります。

#### 1. LeRobot と必要な依存関係を入れる

リポジトリのルートで仮想環境を作ります。すでに LeRobot 用の環境がある場合は、依存関係のインストールだけ実行してください。

```bash
cd /path/to/lerobot
python -m venv .venv
source .venv/bin/activate
pip install -e ".[hilserl,gamepad,feetech]"
```

`gamepad` は PS4 入力用、`feetech` は SO-100 のモーター用です。HIL-SERL のオンライン学習には NVIDIA GPU を推奨します。CPU でも起動できる場合がありますが、学習はかなり遅くなります。

#### 2. ロボット、カメラ、ゲームパッドを確認する

```bash
lerobot-find-port
lerobot-find-cameras opencv
```

この人の環境では `/dev/leader` が leader、`/dev/follower` が follower のポートです。別のPCで同じ名前を使う場合は、udev のシンボリックリンクがそれぞれ正しいUSBデバイスを指すよう設定してください。`lerobot-find-port` でも実際の接続先を確認できます。カメラ一覧から使うカメラの番号、解像度も控えます。PS4 は USB で接続しておくと、最初の設定が簡単です。

leader と follower はそれぞれ個別にキャリブレーションします。まず leader、次に follower の順に接続し、各アームを安全な中間位置に置いて実行します。

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

キャリブレーション中は画面の指示に従い、各関節を無理のない範囲で動かします。`gray_leader` と `white_follower` はキャリブレーション情報を保存するときに使うデバイスIDです。別のIDに変える場合は、この後の設定ファイルでも同じIDを使ってください。

#### 3. URDF と安全な作業範囲を準備する

逆運動学のURDFには [SO-ARM100 リポジトリ](https://github.com/TheRobotStudio/SO-ARM100)の `Simulation/SO101/so101_new_calib.urdf` を使います。SO-100の寸法に対応するモデルです。パスとエンドエフェクタ名 `gripper` を設定に記入してください。

leader アームも使える場合は、次のコマンドで作業範囲を測れます。計測中は leader を動かし、follower がタスクを安全に行える範囲を通します。

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

このコマンドは SO-100 leader と follower の両方を必要とします。下の `end_effector_bounds` の数値は **機材に合わせて実測値へ置き換える欄** です。サンプル値をそのまま実機に使わないでください。設定では関節角度を度で扱うため、follower に `use_degrees: true` を指定します。

#### 4. 成功・失敗ラベル付きのデータを記録する

設定ファイル `examples/tutorial/rl/hilserl_so100/reward_record.json` を作り、次の例を保存します。カメラの `index_or_path`、URDF、`end_effector_bounds` は自分の値に置き換えます。ポートとIDは、この人の環境に合わせて `/dev/follower` と `white_follower` に設定済みです。

```json
{
  "env": {
    "name": "real_robot",
    "fps": 10,
    "robot": {
      "type": "so100_follower",
      "port": "/dev/follower",
      "id": "white_follower",
      "use_degrees": true,
      "cameras": {
        "front": {
          "type": "opencv",
          "index_or_path": 0,
          "fps": 30,
          "width": 640,
          "height": 480
        }
      }
    },
    "teleop": {
      "type": "gamepad",
      "use_gripper": true
    },
    "processor": {
      "control_mode": "gamepad",
      "image_preprocessing": {
        "crop_params_dict": {},
        "resize_size": [128, 128]
      },
      "gripper": {
        "use_gripper": true,
        "gripper_penalty": 0.0
      },
      "reset": {
        "reset_time_s": 5.0,
        "control_time_s": 20.0,
        "terminate_on_success": false
      },
      "inverse_kinematics": {
        "urdf_path": "/path/to/SO-ARM100/Simulation/SO101/so101_new_calib.urdf",
        "target_frame_name": "gripper",
        "end_effector_bounds": {
          "min": ["X_MIN", "Y_MIN", "Z_MIN"],
          "max": ["X_MAX", "Y_MAX", "Z_MAX"]
        },
        "end_effector_step_sizes": {
          "x": 0.01,
          "y": 0.01,
          "z": 0.01
        }
      }
    }
  },
  "dataset": {
    "repo_id": "local/so100_reward_labels",
    "root": "data/so100_reward_labels",
    "task": "pick_and_lift_cube",
    "num_episodes_to_record": 20,
    "replay_episode": null,
    "push_to_hub": false
  },
  "mode": "record",
  "device": "cpu"
}
```

上の `X_MIN` などは説明用の文字列なので、計測した数値に置き換えてから実行します。最初は `push_to_hub` を `false` のままにして、データをローカルに保存します。

```bash
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/reward_record.json
```

記録中は **R1 を押しながら** スティックと L2/R2 でロボットを操作します。初回は目標を「キューブをつかんで持ち上げる」など、5～10秒ほどで終わる単純なタスクにします。

**最初の収録目安：20エピソード（成功 10、失敗 10）** とします。これは始めるための実務上の目安です。公式ガイドは合計20エピソードの例を載せていますが、成功と失敗の固定比率は指定していません。

報酬分類器が学習するラベルはエピソード全体ではなく、各フレームの `reward` です。成功した状態を保って Triangle を押し、いったん離してから何度か押し直すと、その瞬間の画像に成功ラベル `1` が付きます。この設定では `terminate_on_success: false` なので Triangle だけではエピソードが終わりません。成功画像を付け終えたら Cross を押して次へ進みます。失敗状態では、その状態をカメラに映して Cross を押します。Triangle を1回押しただけだと成功ラベルは原則1フレームだけで、残りのフレームは `0` です。

枚数は「成功エピソード10本、失敗エピソード10本」だけで判断せず、まず **成功ラベル付き画像を100枚程度** 集め、失敗・未成功の画像も少なくとも同程度になるよう、物体位置や失敗の仕方に変化をつけて追加収録します。100枚はこの教材での初期目安で、公式に定められた必須数ではありません。予測が不安定なら両方の例を増やします。

#### 5. カメラ画像の ROI を切り出す

タスクに関係するロボット先端、物体、ゴール領域が入るよう ROI を選びます。

```bash
python -m lerobot.rl.crop_dataset_roi \
  --repo-id local/so100_reward_labels \
  --root data/so100_reward_labels \
  --task "pick up the cube and lift it"
```

各カメラ画像で範囲をドラッグし、`c` で確定します。出力データセットは `local/so100_reward_labels_cropped_resized`、ローカルでは `data/so100_reward_labels_cropped_resized` です。出力の `meta/crop_params.json` にある `[top, left, height, width]` を、後述する actor/learner 設定の `crop_params_dict` にも設定します。

#### 6. 報酬分類器を学習する

`examples/tutorial/rl/hilserl_so100/reward_classifier_train.json` を作り、カメラ名 `front` と前段で作った dataset を指定します。複数カメラなら `input_features` に各カメラを追加し、`num_cameras` も同じ数にします。

```json
{
  "dataset": {
    "repo_id": "local/so100_reward_labels_cropped_resized",
    "root": "data/so100_reward_labels_cropped_resized"
  },
  "policy": {
    "type": "reward_classifier",
    "model_name": "helper2424/resnet10",
    "model_type": "cnn",
    "num_cameras": 1,
    "num_classes": 2,
    "hidden_dim": 256,
    "dropout_rate": 0.1,
    "learning_rate": 0.0001,
    "device": "cuda",
    "input_features": {
      "observation.images.front": {
        "type": "VISUAL",
        "shape": [3, 128, 128]
      }
    },
    "push_to_hub": false
  },
  "output_dir": "outputs/so100_reward_classifier",
  "batch_size": 16,
  "num_workers": 4,
  "steps": 5000,
  "log_freq": 10,
  "save_freq": 1000,
  "save_checkpoint": true,
  "eval_freq": 0,
  "wandb": {
    "enable": false
  }
}
```

```bash
lerobot-train \
  --config_path examples/tutorial/rl/hilserl_so100/reward_classifier_train.json
```

学習後のモデルは `outputs/so100_reward_classifier/checkpoints/last/pretrained_model` に保存されます。2値分類の予測が成功画像と失敗画像を見分けるか、数枚ずつ目視で確認します。

#### 7. actor / learner 用設定を作る

公式の [actor-learner 設定例](https://huggingface.co/datasets/lerobot/config_examples/resolve/main/rl/train_config.json)をコピーして、`examples/tutorial/rl/hilserl_so100/train_hilserl.json` として保存します。次の値をこのロボット向けに置き換えます。

- `dataset.repo_id` / `dataset.root`: ROI 処理後のデータセット
- `env.name`: `real_robot`（この LeRobot 版では `env.type` は書かない）
- `env.robot`: `type: so100_follower`、ポート `/dev/follower`、ID `white_follower`、カメラ
- `env.teleop`: `{"type": "gamepad", "use_gripper": true}`
- `env.processor.control_mode`: `gamepad`
- `env.processor.inverse_kinematics`: 4節の URDF、実測 bounds、step size
- `env.processor.image_preprocessing`: 5節の crop params と `[128, 128]`
- `env.processor.reward_classifier.pretrained_path`: 分類器の保存先
- `env.processor.reset.terminate_on_success`: `true`（学習時は分類器の成功判定でエピソードを終える）
- `policy.type`: `sac`、`policy.num_discrete_actions`: `3`（グリッパーの close / stay / open）
- `policy.device`: CUDA マシンなら `cuda`
- `policy.temperature_init`: `0.01` から開始
- `policy.online_steps`: 最初は `100000` 程度にして動作確認
- `policy.push_to_hub`: `false`（ローカル保存）
- `wandb.enable`: アカウント設定前は `false`

SO-100 は6関節なので、policy の観測特徴には画像と `observation.state`（shape `[6]`）を指定します。画像は `[3, 128, 128]`、連続アクションは XYZ の3成分です。離散グリッパー操作を有効にするため `num_discrete_actions` を3にします。設定例に `env.features` / `env.features_map` がない場合は、次の内容を追加します（カメラ名を変えたら `front` も合わせます）。

```json
"features": {
  "front": {"type": "VISUAL", "shape": [128, 128, 3]},
  "agent_pos": {"type": "STATE", "shape": [6]},
  "action": {"type": "ACTION", "shape": [3]}
},
"features_map": {
  "front": "observation.images.front",
  "agent_pos": "observation.state",
  "action": "action"
}
```

#### 8. 学習を開始する

同じ PC 上でターミナルを2つ開きます。最初に learner を起動します。

**ターミナル1：learner**

```bash
python -m lerobot.rl.learner \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl.json
```

learner が gRPC サーバーを起動したら、もう一方で actor を起動します。

**ターミナル2：actor（実機を動かすプロセス）**

```bash
python -m lerobot.rl.actor \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl.json
```

actor が接続するとロボットが動き始めます。方策が危険な方向へ動いたときや動作に失敗したときは、R1 を押し続けて操作を引き取り、スティックとグリッパーで修正します。R1 を離すと方策に戻ります。うまくいったエピソードは Triangle、失敗したエピソードは Cross で記録します。はじめは介入し、学習が進むにつれて介入回数を減らします。

停止するときは **ターミナル2の actor から `Ctrl+C`、次にターミナル1の learner で `Ctrl+C`** を押します。出力先 `outputs/so100_hilserl` に checkpoint とログが保存されます。再実行時は `output_dir` を別名にするか、意図した checkpoint から resume してください。

## 環境の設定

ローカルの設定ファイルには機材ごとの値を設定します。公開する設定例には実ポート名や個人のファイルパスを書かず、各自の環境で値を埋めてください。

- follower / leader のデバイスパス
- カメラ名とデバイス番号
- URDF の場所、エンドエフェクタの座標範囲
- データセットと報酬分類器の Hub ID
- GPU / CPU の選択

Hub へのアップロードは、公開先・データ内容を確認してから明示的に有効にしてください。データセットや学習済み重みはこの教材に含めません。必要なら Hugging Face Hub などに別途公開し、README に取得先とライセンスを記載してください。

## 実機の安全

- 最初は低速・小さい動作範囲で確認し、ロボットをすぐ停止できる位置にいてください。
- 作業空間から人や壊れやすい物を離してください。
- 緊急停止の方法を確認してから actor を起動してください。
- actor と learner の設定、カメラ入力、介入デバイスを確認せずに長時間運転しないでください。

## このフォルダを GitHub に公開するとき

この教材だけを別の GitHub リポジトリで共有する場合は、LeRobot のライセンスと貢献者向けルールを確認し、LeRobot 本体の変更は fork 上で管理してください。個人用モデル重み、収録データ、実機ログ、ローカル設定、Hub の認証情報、別リポジトリの `.git` ディレクトリは教材リポジトリに含めないでください。SO-ARM100 の CAD 資産を再配布する場合は、元リポジトリのライセンスと帰属表示も維持してください。

### 関連資料

- [LeRobot HIL-SERL 実機ガイド](../../../../docs/source/hilserl.mdx)
- [LeRobot HIL-SERL シミュレーションガイド](../../../../docs/source/hilserl_sim.mdx)
- [HIL-SERL の元論文](https://arxiv.org/abs/2309.02709)
- [SO-ARM100 / SO-101 の組み立て資料](https://github.com/TheRobotStudio/SO-ARM100)
