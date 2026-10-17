# LinuxでSO-101のHIL-SERLデータを集める

この手順は、Linux PC、SO-101 follower、PS4（DualShock 4）、USBカメラを使い、「キューブをつかんで持ち上げる」操作データを**学習せずに収録**するためのものです。コマンドはリポジトリのルート（`lerobot` ディレクトリ）で実行します。

> **設定について**: JSONの `/dev/ttyACM0`、カメラパス、URDFパスはサンプルです。自分のPCで見つかった follower ポート、カメラの安定パス、URDFの場所に合わせて設定してください。

## 実機データ収集の順番

### 1. リポジトリと仮想環境を開く

まだこの版を取得していない場合は、GitHubの `codex/hilserl-so101-tutorial` ブランチをcloneします。

```bash
git clone --branch codex/hilserl-so101-tutorial --single-branch https://github.com/Gannbayar/lerobot.git
cd lerobot
```

すでにclone済みなら、その `lerobot` ディレクトリに移動します。初回セットアップがまだの場合だけ、依存関係を入れます。

```bash
python3 -m venv .venv
.venv/bin/pip install -e ".[hilserl,gamepad,feetech]"
```

SO-101のURDFはLeRobot本体とは別の公式リポジトリから取得します。リポジトリのルートで次を実行してください（すでに `../work/SO-ARM100` がある場合は飛ばします）。

```bash
mkdir -p ../work
git clone https://github.com/TheRobotStudio/SO-ARM100.git ../work/SO-ARM100
```

### 2. USBとアクセス権を確認する

follower、カメラ、PS4をUSBでつなぎます。follower のポートとカメラのパスはPCごとに異なります。カメラ番号だけの `/dev/videoN` は挿し直しで変わることがあるため、`lerobot-find-cameras opencv` の結果から自分のカメラを選び、そのパスを各JSONの `index_or_path` に設定します。3つのJSON（動作確認、範囲確認、録画）すべてで、`robot.port`、`robot.id`、カメラの `index_or_path`、`inverse_kinematics.urdf_path` を自分の機材に合わせます。

確認コマンド:

```bash
.venv/bin/lerobot-find-port
.venv/bin/lerobot-find-cameras opencv
```

シリアルポートにアクセスできないときは、`dialout` グループに入っているか確認します。

```bash
groups
```

出力に `dialout` がなければ、次を実行してからUbuntuからログアウトし、再ログインします。

```bash
sudo usermod -aG dialout "$USER"
```

### 3. followerをキャリブレーションする

キャリブレーション済みで、アームが通常どおり動く場合は飛ばします。やり直す場合は、周囲を片付け、アームを動かせる状態にして次を実行します。

```bash
sg dialout -c '.venv/bin/lerobot-calibrate --robot.type=so101_follower --robot.port=/dev/ttyACM0 --robot.id=so101_follower'
```

画面の案内に従って関節を動かします。キャリブレーション中に関節を無理に押し込まないでください。

### 4. カメラとPS4を表示して、短く動作確認する

`gamepad_check.json` は操作確認専用です。`mode` は `null` なので、データセットを作りません。

```bash
sg dialout -c '.venv/bin/python -m lerobot.rl.gym_manipulator --config_path examples/tutorial/rl/hilserl_so100/gamepad_check.json'
```

画面でカメラ映像を確認します。ロボットの先端とキューブが同時に映るようカメラを置きます。PS4のスティックを少し倒して動くことを確かめ、端末で `Ctrl+C` を押して終了します。

| PS4 | 動作 |
| --- | --- |
| R1を押しながら左スティック | X/Y方向へ動かす |
| R1を押しながら右スティック上下 | Z方向へ動かす |
| L2 / R2 | グリッパーを閉じる / 開く |
| Triangle（△） | 成功ラベルを付ける |
| Cross（×） | 失敗としてエピソードを終了 |
| Square（□） | 現在のエピソードを破棄してやり直す |

スティックで動かすときは常にアームを見て、台やロボット本体に近づきすぎたらすぐ `Ctrl+C` で停止します。

### 5. キューブに届く動作範囲を確認する

次の設定は、このSO-101の読み取り姿勢を中心に作った**暫定的な範囲確認用**です。別のPCやアームでは実際に測った安全限界ではありません。データ録画には使わず、まず映像を見ながら先端がキューブまで届くかだけ確認してください。

```bash
sg dialout -c '.venv/bin/python -m lerobot.rl.gym_manipulator --config_path examples/tutorial/rl/hilserl_so100/gamepad_range_check.json'
```

この設定も `mode: null` のため録画しません。範囲に届かない場合は、`gamepad_range_check.json` の `env.processor.inverse_kinematics.end_effector_bounds` を少しずつ調整して再確認します。`min` と `max` は `[x, y, z]` のメートル単位です。値を一度に大きく広げず、テーブル面やアーム本体に入らない範囲を確認してください。安全な範囲を確認できるまでは、次の録画へ進みません。

### 6. 録画用設定を確認する

録画設定は [`so101_cube_lift_record.json`](so101_cube_lift_record.json) に用意してあります。10エピソードをローカルの `data/so101_cube_lift_demo` に保存し、Triangleで成功エピソード、Crossで失敗エピソードを終了します。Hubへのアップロードはしません。

範囲は手順5の確認用設定と同じです。**自分のPCでPS4を使い、キューブまで安全に動かせた場合だけ録画へ進みます。** 途中で台やロボット本体に近づいた場合は録画せず停止し、設定範囲を調整します。動作に不安があるときは `mode` を `null` に戻して再確認してください。

### 7. デモを録画する

```bash
sg dialout -c '.venv/bin/python -m lerobot.rl.gym_manipulator --config_path examples/tutorial/rl/hilserl_so100/so101_cube_lift_record.json'
```

各エピソードでPS4を使い、キューブをつかんで持ち上げます。成功したらTriangle、失敗として終えるときはCross、やり直すときはSquareを押します。設定したエピソード数が終わると、データセットは `data/so101_cube_lift_demo` に保存されます。途中で安全に停止する場合は `Ctrl+C` を押します。

### 8. 保存結果を確認する

```bash
ls -lah data/so101_cube_lift_demo
```

エピソードの動画と操作が正しく記録されたことを確認してから、必要に応じて追加収録します。このガイドはデータ収集までです。報酬分類器、actor/learner、ポリシーの学習コマンドは実行しません。

## 送ってくれたHILデータ収集ページについて

[Human-In-the-Loop Data Collection](https://huggingface.co/docs/lerobot/hil_data_collection) は、学習済みポリシーを実機で動かし、人が介入したデータを追加するDAggerの手順です。最初のデモデータを作る本手順とは段階が異なります。今は学習せずデータだけを集めるため、上のHIL-SERL `mode: record` を使います。

---

# LinuxでSO-101 / HIL-SERLシミュレーション

実機のデータ収集手順は、このページ冒頭の「実機データ収集の順番」を参照してください。以下はシミュレーションの起動方法です。

この手順はMuJoCoのGUIを表示できるLinuxデスクトップ向けです。SO-101のシーン表示と、HIL-SERL公式シミュレーターは別の環境です。

## 1. LeRobot環境を準備する

LeRobotリポジトリのルートで仮想環境を有効にし、シミュレーション用依存関係を入れます。

```bash
cd /path/to/lerobot
python3 -m venv .venv  # 初回のみ。既に .venv がある場合は飛ばす
source .venv/bin/activate
python -m pip install -e ".[hilserl]"
```

GUIを表示するには、LinuxのデスクトップセッションとOpenGL対応ディスプレイが必要です。SSH先など画面のない環境ではこのビューアは開きません。

## 2. SO-101モデルを取得する

公式の [SO-ARM100リポジトリ](https://github.com/TheRobotStudio/SO-ARM100)にSO-101のMuJoCoモデルがあります。まだ取得していない場合だけ実行します。

```bash
cd ~
git clone --depth 1 https://github.com/TheRobotStudio/SO-ARM100.git
```

## 3. 紙コップ・コーヒー・砂糖ブロックを含むシミュレーションを開く

```bash
cd /path/to/lerobot
source .venv/bin/activate
python examples/tutorial/rl/hilserl_so100/simulate_so101_coffee.py
```

SO-101、550×400 mmの青黒チェックマット、紙コップ、コーヒー、砂糖ブロックが表示されます。マット端はロボットベースの後ろ側に合うようにし、ロボットをマットに対して約50 mm前へ寄せています。木の台は追加していません。ジョイントはビューアの **Control** パネルで動かします。カメラを使うには、起動後にビューア上部の **Camera** メニューを開き、`wrist_camera`、`robot_camera`、`side_camera`、`front_camera` のいずれかを選びます。`wrist_camera` は画像の丸印付近に置き、アームから約3.5 cm離してグリッパーの把持点を向きます。カメラ姿勢は回転する `gripper` リンクに固定しているため、`wrist_roll` と一緒にカメラ本体と映像の向きが回ります。他の3台は配置図の高さ（610・440・125 mm）に合わせた固定視点で、マット中央を見るよう傾けています。位置・角度は配置資料からの近似です。これらはビューアの視点で、HIL-SERLに画像を送るカメラ入力ではありません。マットの格子幅も写真からの概算です。SO-ARM100を別の場所に置いた場合は、シーンXMLのパスを指定します。

カメラの位置や向きを自分で調整する場合は、共通ガイドの[カメラ調整方法](README_ja.md#カメラ位置と向きを自分で調整する)を参照してください。

```bash
python examples/tutorial/rl/hilserl_so100/simulate_so101_coffee.py \
  --scene "$HOME/SO-ARM100/Simulation/SO101/scene.xml"
```

紙コップは上の直径7.3 cm、底の直径5 cm、高さ8 cmに合わせた白い簡易形状です。壁はMuJoCoの標準形状を組み合わせて近似しています。コーヒーは色と質量を持つ剛体で、液体の揺れやこぼれは計算しません。砂糖ブロックは約18 mm角の剛体です。このシーンはSO-101の姿勢や物体との接触を確認するもので、HIL-SERL用タスクや学習設定は含みません。

## 4. HIL-SERLのシミュレーションを開く

LeRobotの `gym_hil` 環境はSO-101ではなくFranka Pandaです。Linuxでは通常の `python` で起動します。

```bash
cd /path/to/lerobot
source .venv/bin/activate
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

この画面はHIL-SERLの操作手順を試すためのPanda用です。SO-101のモデルを動かしたい場合は、上の専用シーンを使ってください。オンライン学習にはNVIDIA GPUを推奨します。詳細なHIL-SERL実機手順と安全上の注意は[共通ガイド](README_ja.md)を参照してください。

