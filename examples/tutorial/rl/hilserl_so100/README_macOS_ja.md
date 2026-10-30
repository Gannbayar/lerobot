# macOSでSO-101 / HIL-SERLシミュレーション

この手順は MuJoCo のGUIを開けるmacOS向けです。SO-101のシーン表示と、HIL-SERL公式シミュレーターは別の環境です。

## 1. LeRobot環境を準備する

LeRobotリポジトリのルートで仮想環境を有効にし、シミュレーション用依存関係を入れます。

```bash
cd /path/to/lerobot
python3 -m venv .venv  # 既に .venv がある場合は飛ばす
source .venv/bin/activate
python -m pip install -e ".[hilserl]"
```

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

SO-101、550×400 mmの青黒チェックマット、紙コップ、コーヒー、砂糖ブロックが表示されます。マット端はロボットベースの後ろ側に合うようにし、ロボットをマットに対して約50 mm前へ寄せています。木の台は追加していません。ジョイントはビューアの **Control** パネルで動かします。カメラを使うには、起動後にビューア上部の **Camera** メニューを開き、`wrist_camera`、`robot_camera`、`side_camera`、`front_camera` のいずれかを選びます。`wrist_camera` は画像の丸印付近に置き、アームから約3.5 cm離してグリッパーの把持点を向きます。カメラ姿勢は回転する `gripper` リンクに固定しているため、`wrist_roll` と一緒にカメラ本体と映像の向きが回ります。他の3台は配置図の高さ（610・440・125 mm）に合わせた固定視点で、マット中央を見るよう傾けています。位置・角度は配置資料からの近似です。これらはビューアの視点で、HIL-SERLに画像を送るカメラ入力ではありません。マットの格子幅も写真からの概算です。別の場所にSO-ARM100を置いた場合は、シーンXMLのパスを指定します。

カメラの位置や向きを自分で調整する場合は、共通ガイドの[カメラ調整方法](README_ja.md#カメラ位置と向きを自分で調整する)を参照してください。

```bash
cd /path/to/lerobot
source .venv/bin/activate
python examples/tutorial/rl/hilserl_so100/simulate_so101_coffee.py \
  --scene "$HOME/SO-ARM100/Simulation/SO101/scene.xml"
```

紙コップは上の直径7.3 cm、底の直径5 cm、高さ8 cmに合わせた白い簡易形状です。壁はMuJoCoの標準形状を組み合わせて近似しています。コーヒーは色と質量を持つ剛体で、液体の揺れやこぼれは計算しません。砂糖ブロックは約18 mm角の剛体です。

## 4. SO-101をHIL操作してデモを収録する

このリポジトリには、SO-101のシーンをHILキーボード操作とLeRobotデータセット収録につなぐ実験用環境があります。macOSではMuJoCo GUIを `mjpython` で起動します。

```bash
cd /path/to/lerobot
source .venv/bin/activate
mjpython -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

成功・失敗デモを保存する場合は収録用設定を起動します。最初にSpaceで介入を有効にし、砂糖をカップに入れる試行を行います。Enterで成功、Escで失敗を記録します。

```bash
mjpython -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim_record.json
```

初回は20試行を `data/so101_coffee_keyboard_demos` に保存します。収録の中身は次で確認できます。

```bash
lerobot-dataset-viz \
  --repo-id local/so101_coffee_keyboard_demos \
  --root data/so101_coffee_keyboard_demos \
  --episode-index 0
```

このデータは手動ラベル付きの初期デモです。A6000 Linux機で学習する場合は[学習用設定](train_hilserl_so101_sim.json)をLinux側にも配置し、データセットをその設定の`dataset.root`に置きます。GPUでのactor/learner実行はまだ検証できていません。公式 `gym_hil` 標準タスクはFranka Pandaです。実機手順と安全上の注意は[共通ガイド](README_ja.md)を参照してください。

この作業環境では `mjpython` 自体がコード実行時に終了コード134で異常終了し、GUIとカメラ画像の表示までは確認できませんでした。ターミナルからも同じ終了になる場合、収録はA6000搭載Linux機で実行してください。

