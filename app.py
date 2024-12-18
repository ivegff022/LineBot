from flask import Flask, request, abort
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import *
import os
from pydub import AudioSegment
from gtts import gTTS
import speech_recognition as sr

app = Flask(__name__)

# 使用環境變數存儲 LINE Channel Access Token 和 Secret
line_bot_api = LineBotApi(os.environ['CHANNEL_ACCESS_TOKEN'])
handler = WebhookHandler(os.environ['CHANNEL_SECRET'])

@app.route("/callback", methods=['POST'])
def callback():
    # 取得 LINE 的請求
    signature = request.headers['X-Line-Signature']
    body = request.get_data(as_text=True)
    app.logger.info("Request body: " + body)

    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        abort(400)

    return 'OK'

# 處理 FollowEvent 事件 (用戶開始關注機器人)
@handler.add(FollowEvent)
def handle_follow(event):
    welcome_message = "你好，我是XR製作顧問"
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text=welcome_message)
    )

# 處理文字訊息事件
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):
    user_text = event.message.text
    if user_text == "你好":
        response_text = "你好"
        # 生成語音訊息
        tts = gTTS(response_text, lang="zh-TW")
        tts_audio_path = "response.mp3"
        tts.save(tts_audio_path)
        
        # 上傳語音檔案到公開網址（你需要替換成自己的檔案伺服器或服務器）
        audio_message = AudioSendMessage(
            original_content_url=f"https://your-server-url/{tts_audio_path}",  # 替換為你的伺服器 URL
            duration=2000  # 語音訊息的時長（以毫秒為單位）
        )
        
        line_bot_api.reply_message(event.reply_token, audio_message)

# 處理語音訊息事件
@handler.add(MessageEvent, message=AudioMessage)
def handle_audio_message(event):
    # 下載語音訊息
    audio_file_path = f"{event.message.id}.m4a"
    audio_content = line_bot_api.get_message_content(event.message.id)
    with open(audio_file_path, 'wb') as f:
        f.write(audio_content.content)
    
    # 轉換語音檔案格式
    wav_path = f"{event.message.id}.wav"
    audio = AudioSegment.from_file(audio_file_path, format="m4a")
    audio.export(wav_path, format="wav")
    
    # 使用 SpeechRecognition 將語音轉文字
    recognizer = sr.Recognizer()
    with sr.AudioFile(wav_path) as source:
        audio_data = recognizer.record(source)
        try:
            recognized_text = recognizer.recognize_google(audio_data, language="zh-TW")
        except sr.UnknownValueError:
            recognized_text = "無法辨識語音"
    
    # 根據辨識結果回應
    if recognized_text == "你好":
        response_text = "你好"
        # 生成語音回應
        tts = gTTS(response_text, lang="zh-TW")
        tts_audio_path = "response.mp3"
        tts.save(tts_audio_path)
        
        # 傳送語音回應（需要伺服器有公開網址）
        audio_message = AudioSendMessage(
            original_content_url=f"https://your-server-url/{tts_audio_path}",  # 替換為你的伺服器 URL
            duration=2000
        )
        line_bot_api.reply_message(event.reply_token, audio_message)
    else:
        response_text = f"你說的是: {recognized_text}"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=response_text))
    
    # 清理檔案
    os.remove(audio_file_path)
    os.remove(wav_path)

if __name__ == "__main__":
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
