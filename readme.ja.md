<!--[![Discord Bots](https://top.gg/api/widget/status/961521106227974174.svg)](https://top.gg/bot/716496407212589087) [![Discord Bots](https://top.gg/api/widget/servers/716496407212589087.svg)](https://top.gg/bot/716496407212589087) -->
![Discord](https://img.shields.io/discord/961521739748212776?label=supportFree-rt&logo=discord)

# Free RT Bot
discordのBotであるRTのフリー版です。  
RTはもともと無料で利用できましたが、有料になったためこのリポジトリが作成されました。  
RTはBotが1台だけで済むように作成された多機能で便利なBotです。  
ウェブ認証などのために`rt-backend`とWebSocketで通信も行います。  
RTについて知らない人は[ここ](https://rt-bot.com/)を見てみましょう。  
Free RTについて知らない人は[ここ](https://free-rt.com/)を見てみましょう。

## LICENSE
`BSD 4-Clause License` (`LICENSE`ファイルに詳細があります。)

## Contributing
[contributing](https://github.com/Free-RT/rt-bot/blob/main/contributing)をご覧ください。

## Free RT 開発状況
導入サーバー数が100サーバーに到達したためbotの認証が必要になります。認証が終わるまではbotの導入ができないのでご迷惑をおかけしますがしばらくお待ちください...  
_詳しくは公式サーバーのお知らせチャンネルやgithubのissues, discussionsを参照してください。_

## Installation
### Depedencies
必要なものです。

* Python 3.9以上
* MySQL または MariaDB
* `requirements.txt`にあるもの全て。
* `rt-backend`の実行 (認証等のバックエンドを必要とする機能を使う場合)

### 起動手順
1. 必要なものを`pip install -r requirements.txt`でインストールをします。
2. 必要なTOKENなどを`auth.template.json`を参考に`auth.json`に書き込む。
3. `util`に`rt-module`リポジトリをそのまま(srcだけ置くとかはしないでください)置いてフォルダの名前を`rt_module`にする。
4. `rt-backend`リポジトリにあるプログラムを動かす。
   (任意です。認証等のバックエンドを必要とするものを動かしたい場合は動かす必要があります。)
5. `python3 main.py test`でテストを実行する。
   (この際TOKENは`auth.json`の`test`のキーにあるものが使用されます。)

※ もし読み上げを動かしたいのなら`cogs/tts`にある`readme.md`を読んでください。

### 本番環境での実行
起動コマンドは`sudo -E python3 main.py production`で`auth.json`のTOKENで`production`のTOKENが必要となります。  
NOTE: `run.sh`の起動でも動きます。
