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

SO-101、テーブル、紙コップ、コーヒー、砂糖ブロックがMuJoCoビューアに表示されます。ジョイントはビューアの **Control** パネルで動かします。SO-ARM100を別の場所に置いた場合は、シーンXMLのパスを指定します。

```bash
python examples/tutorial/rl/hilserl_so100/simulate_so101_coffee.py \
  --scene "$HOME/SO-ARM100/Simulation/SO101/scene.xml"
```

紙コップは白い壁と底を組み合わせた簡易形状です。コーヒーは色と質量を持つ剛体で、液体の揺れやこぼれは計算しません。砂糖ブロックは約18 mm角の剛体です。このシーンはSO-101の姿勢や物体との接触を確認するもので、HIL-SERL用タスクや学習設定は含みません。

## 4. HIL-SERLのシミュレーションを開く

LeRobotの `gym_hil` 環境はSO-101ではなくFranka Pandaです。Linuxでは通常の `python` で起動します。

```bash
cd /path/to/lerobot
source .venv/bin/activate
python -m lerobot.rl.gym_manipulator \
  --config_path examples/tutorial/rl/hilserl_so100/gym_hil_sim.json
```

この画面はHIL-SERLの操作手順を試すためのPanda用です。SO-101のモデルを動かしたい場合は、上の専用シーンを使ってください。オンライン学習にはNVIDIA GPUを推奨します。詳細なHIL-SERL実機手順と安全上の注意は[共通ガイド](README_ja.md)を参照してください。

