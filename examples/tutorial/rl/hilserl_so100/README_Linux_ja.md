# LinuxでSO-101 / HIL-SERLシミュレーション

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

SO-101、550×400 mmの青黒チェックマット、紙コップ、コーヒー、砂糖ブロックが表示されます。マットはロボットの正面（アームが伸びる側）に置いてあります。木の台は追加していません。ジョイントはビューアの **Control** パネルで動かします。カメラを使うには、起動後にビューア上部の **Camera** メニューを開き、`wrist_camera`、`robot_camera`、`side_camera`、`front_camera` のいずれかを選びます。`wrist_camera` はグリッパーに取り付けた視点で、アームに追従します。他の3台は配置図の高さ（610・440・125 mm）に合わせた固定視点で、マット中央を見るよう傾けています。位置・角度は配置資料からの近似です。これらはビューアの視点で、HIL-SERLに画像を送るカメラ入力ではありません。マットの格子幅も写真からの概算です。SO-ARM100を別の場所に置いた場合は、シーンXMLのパスを指定します。

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

