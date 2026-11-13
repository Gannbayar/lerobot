# LinuxでSO-101 / HIL-SERLシミュレーション

実機のUSB接続からデモ収録・学習・評価まで進める場合は、[Linux実機HIL-SERLガイドブック](GUIDEBOOK_Linux_ja.md)を参照してください。このページはシミュレーションの起動方法を説明します。

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

紙コップは上の直径7.3 cm、底の直径5 cm、高さ8 cmに合わせた白い簡易形状です。壁はMuJoCoの標準形状を組み合わせて近似しています。コーヒーは色と質量を持つ剛体で、液体の揺れやこぼれは計算しません。砂糖ブロックは約18 mm角の剛体です。

## 4. HIL-SERLのシミュレーションを開く

このリポジトリには、上記SO-101シーンをHILキーボード操作とLeRobotデータセット収録につなぐ実験用環境があります。Linuxでは通常の `python` で起動します。

```bash
cd /path/to/lerobot
source .venv/bin/activate
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

この設定は画面と操作の確認用で、データセットは作りません。最初にSpaceで介入を有効にし、矢印キー・Shift・Ctrlで操作します。成功・失敗デモを収録する場合は次を起動し、砂糖をカップに入れる試行を行います。Enterで成功、Escで失敗を記録します。

```bash
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim_record.json
```

初回は20試行が保存されます。品質確認は `lerobot-dataset-viz --repo-id local/so101_coffee_keyboard_demos --root data/so101_coffee_keyboard_demos --episode-index 0` で行います。保存されたデモは以下の学習設定の初期データです。

### A6000 2枚でactor/learnerを起動する

`train_hilserl_so101_sim.json` はオフライン初期データを読み、SO-101環境でオンラインHIL-SERLを実行する実験設定です。`dataset.root` が上記収録先、観測入力は前方・手首カメラと18次元状態です。SACの連続出力3軸にグリッパーの離散3択を加えて4成分の環境操作にします。設定の読み込みとpolicy出力形状（4成分）はMac上で確認済みですが、GPUでのactor/learner実行は未検証です。

収録データがLinux機の同じパスにあり、`nvidia-smi -L` でGPUを確認した後、2つのターミナルで起動します。

**ターミナル1：learner（GPU 0）**

```bash
CUDA_VISIBLE_DEVICES=0 python -m lerobot.rl.learner \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl_so101_sim.json
```

**ターミナル2：actorとシミュレーション（GPU 1）**

```bash
CUDA_VISIBLE_DEVICES=1 python -m lerobot.rl.actor \
  --config_path examples/tutorial/rl/hilserl_so100/train_hilserl_so101_sim.json
```

設定の `device: "cuda"` は各プロセスで見えるGPUに割り当てられます。まず100〜数百ステップで接続・操作・checkpoint出力を確認し、継続学習前にログとデータを点検してください。デモ収録が未完了なら、先に収録を済ませます。現時点でカスタムSO-101環境のオンライン学習成功は確認できていません。公式 `gym_hil` の標準タスクはFranka Pandaです。詳細な実機手順は[共通ガイド](README_ja.md)を参照してください。

