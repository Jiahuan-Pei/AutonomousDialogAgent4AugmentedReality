using System.Collections;
using System.Collections.Generic;
using UnityEngine;
using System;
using System.Linq;
using System.Net.Sockets;
using System.Net.WebSockets;
using System.Security.Cryptography;
using System.Text;
using System.Threading;
using Image = UnityEngine.UI.Image;
using UnityEngine.Android;

public class AudioTest : MonoBehaviour {
    private string AppId = "1308717093";
    private string APISecretID = "AKID1tXfdOvEH6iAbw48861kOvGPq9GKBuXT";
    private string APISecretKey = "ucCh05zh8MNFuy1uacfW9Xq00ylLglMs";

    public AudioClip RecordedClip;
    ClientWebSocket audioWebSocket;
    private CancellationToken ct;

    public GameObject SendOptionOBJ;

    public Sprite[] micPics; // 开始/结束麦克风的数组
    public Image micImg; // 小车当前零件图

    public bool isSpeaking = false;
    public bool isRecording = false;

    public Dictionary<string, string> myInstruction = new Dictionary<string, string>();
    public List<string> optionList = new List<string>

    public string getUrl(string uriStr) {
        DateTime _1970 = new DateTime(1970, 1, 1, 0, 0, 0, 0);
        DateTime now = DateTime.Now;
        int nowSec = (int)(now - _1970).TotalSeconds; // 当前unix时间戳
        int ddlSec = nowSec + 86400; // 握手签名过期时间戳
        int nonce = 1234567890; // 随机数10位

        var requestParameters = new Dictionary<string, string>(); // 写入握手参数
        requestParameters.Add("secretid", APISecretID);
        requestParameters.Add("timestamp", nowSec.ToString());
        requestParameters.Add("expired", ddlSec.ToString());
        requestParameters.Add("nonce", nonce.ToString());
        requestParameters.Add("engine_model_type", "16k_zh");
        requestParameters.Add("voice_id", "0"); // 音频流识别全局唯一标识，一个 websocket 连接对应一个
        requestParameters.Add("needvad", "1"); // 静音三秒则切分
        // requestParameters.Add("vad_silence_time", "2000"); // 静音两秒则切分，此参数建议不要随意调整，可能会影响识别效果
        requestParameters.Add("voice_format", "1"); // pcm格式

        var items = requestParameters.OrderBy(o => o.Key, StringComparer.Ordinal);
        string myParameters = ""; // 按照字典序排序的请求参数
        foreach (var item in items)
            myParameters += item.Key + "=" + item.Value + "&";
        myParameters = myParameters.TrimEnd('&'); // 去掉最后的"&"

        string beforeBase64 = "asr.cloud.tencent.com/asr/v2/" + AppId + "?" + myParameters;
        HMACSHA1 secKey = new HMACSHA1(Encoding.UTF8.GetBytes(APISecretKey)); // 获得秘钥
        string signature = Convert.ToBase64String(secKey.ComputeHash(Encoding.UTF8.GetBytes(beforeBase64)));

        string signatureEncodeUrl = System.Web.HttpUtility.UrlEncode(signature); // 将 signature 值进行 url encode
        string url = string.Format(uriStr + myParameters + "&signature=" + signatureEncodeUrl); // 拼接得到最终url

        return url;
    }

    private void Start() {
        Permission.RequestUserPermission("android.permission.WRITE_EXTERNAL_STORAGE");
        Permission.RequestUserPermission("android.permission.READ_EXTERNAL_STORAGE");
        Permission.RequestUserPermission("android.permission.INTERNET");
        Permission.RequestUserPermission("android.permission.RECORD_AUDIO");

        SendOptionOBJ = GameObject.Find("UploadAndBlockTrans");
        setMap();

        micImg.sprite = micPics[0];
    }

    public void clickSpeak() {
        if (isSpeaking) {
            isSpeaking = false;
            endSpeech();
            SendOptionOBJ.SendMessage("printTipsInfo", "关闭语音交互");
        }
        else {
            isSpeaking = true;
            startSpeech();
            SendOptionOBJ.SendMessage("printTipsInfo", "打开语音交互");
        }
    }

    private void startSpeech() {
        // Debug.Log(getUrl("wss://asr.cloud.tencent.com/asr/v2/" + AppId + "?"));
        micImg.sprite = micPics[1];
        startSpeechRecongnition();
    }

    private void endSpeech() {
        isSpeaking = false;
        micImg.sprite = micPics[0];
        if (audioWebSocket.State != WebSocketState.Open) // 服务器断连
            return;

        string message = "{\"type\": \"end\"}";
        audioWebSocket.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(message)), WebSocketMessageType.Text,
            true,
            ct); //发送数据
        StartCoroutine(stopSpeechRecongnition());
    }
// We introduce dialogue agent (DA) to avoid this types of hard coding, so that the DA can provide the "command" to VR system
//    private void setMap() {
//        myInstruction.Clear();
//        myInstruction.Add("开始", "startAssemble");
//        myInstruction.Add("启动", "startAssemble");
//        myInstruction.Add("结束", "FinishedVideo");
//        myInstruction.Add("完成", "FinishedVideo");
//
//        myInstruction.Add("上一步", "FrontStep");
//        myInstruction.Add("上一部", "FrontStep");
//        // myInstruction.Add("前面", "FrontStep");
//        myInstruction.Add("后退", "FrontStep");
//        myInstruction.Add("下一步", "NextStep");
//        myInstruction.Add("下一部", "NextStep");
//        myInstruction.Add("继续", "NextStep");
//        myInstruction.Add("拼好了", "NextStep");
//        myInstruction.Add("拼好咯", "NextStep");
//        myInstruction.Add("拼好啦", "NextStep");
//        // myInstruction.Add("后面", "NextStep");
//        myInstruction.Add("前进", "NextStep");
//        myInstruction.Add("重复", "ReShow");
//        myInstruction.Add("重新", "ReShow");
//        myInstruction.Add("不太清楚", "ReShow");
//        myInstruction.Add("不太明白", "ReShow");
//        myInstruction.Add("没看懂", "ReShow");
//        myInstruction.Add("再看一次", "ReShow");
//
//        myInstruction.Add("放大", "Enlarge");
//        myInstruction.Add("变大", "Enlarge");
//        myInstruction.Add("缩小", "Shrink");
//        myInstruction.Add("变小", "Shrink");
//
//        myInstruction.Add("细节", "Explode");
//        myInstruction.Add("恢复", "Recover");
//    }
    // pp added: all functions/services the VR system can provide with.
    private void setMap() {
        optionList.Clear();
        // shared functions with VLM
        optionList.Add("startAssemble")
        optionList.Add("FrontStep")
        optionList.Add("NextStep")
        optionList.Add("Explode")
        optionList.Add("Recover")
        optionList.Add("FinishedVideo")
        // functions only for ASR
        optionList.Add("ReShow")
        optionList.Add("Enlarge")
        optionList.Add("Shrink")
    }
//

    // 获取unity录音的数据流AudioClip转化为byte[],需要每隔一段时间发送数据直到录音结束。
    // 参数start是录音的位置与音频采样率有关，同样length也是采样长度。
    // 举个例子，如果采样率是16000，那么start=16000的位置就是从获取一秒后语音流位置，以此类推。
    // 如果采样率是16000，start=16000x,length=16000y则是从x秒开始录音长度为y的一段语音流数据。
    public static byte[] getFragmentAudioStream(int start, int length, AudioClip recordedClip) {
        float[] soundData = new float[length];
        recordedClip.GetData(soundData, start);

        int rescaleFactor = 32767; // 缩放因子 32767
        byte[] outData = new byte[soundData.Length * 2];
        for (int i = 0; i < soundData.Length; i++) {
            short temshort = (short)(soundData[i] * rescaleFactor);
            byte[] temdata = BitConverter.GetBytes(temshort);
            outData[i * 2] = temdata[0];
            outData[i * 2 + 1] = temdata[1];
        }

        return outData;
    }

    public void startSpeechRecongnition() { // 开始语音识别
        if (audioWebSocket != null && audioWebSocket.State == WebSocketState.Open) {
            return;
        }

        RecordedClip = Microphone.Start(null, false, 1800, 16000); // 当前测试长度为0.5h 采样率16k
        isRecording = true;
        connectAudioWebSocketWebSocket();
    }

    public void OnDestroy() {
        if (audioWebSocket != null)
            audioWebSocket.Abort();
        Microphone.End(null);
    }

    private static bool IsSilent(float[] audioData) {
        float energy = 0f;
        float energyThreshold = 0.00001f;
        for (int i = 0; i < audioData.Length; i++) {
            energy += audioData[i] * audioData[i];
        }

        energy /= audioData.Length;
        return energy < energyThreshold;
    }

    public IEnumerator stopSpeechRecongnition() { // 结束语音识别处理
        Microphone.End(null);
        yield return new WaitUntil(() => audioWebSocket.State != WebSocketState.Open); // 等待连接客户端关闭
    }

    void sendAudioData(byte[] audio) { // 向服务器发送音频信息
        if (audioWebSocket.State != WebSocketState.Open) // 服务器断连
            return;

        audioWebSocket.SendAsync(audio, WebSocketMessageType.Binary, true, ct); // 发送数据
    }

    void sendEndMessage(ClientWebSocket socket, CancellationToken ct) { // 向服务器发送结束处理信息
        if (socket.State != WebSocketState.Open) // 服务器断连
            return;

        string message = "{\"type\": \"end\"}";
        socket.SendAsync(new ArraySegment<byte>(Encoding.UTF8.GetBytes(message)), WebSocketMessageType.Text, true,
            ct); //发送数据
        audioWebSocket.CloseOutputAsync(WebSocketCloseStatus.NormalClosure, "Closing connection",
            CancellationToken.None); // todo 取消令牌
        StartCoroutine(stopSpeechRecongnition());
    }

    public void restartVoice() {
        if (isSpeaking) {
            isSpeaking = false;
            endSpeech();
            isSpeaking = true;
            startSpeech();
        }
        else {
            isSpeaking = true;
            startSpeech();
        }
    }

    IEnumerator sendAudioStream(ClientWebSocket socket, CancellationToken ct) { // 持续发送音频流
        yield return new WaitWhile(() => Microphone.GetPosition(null) <= 0); // 等待开始录音

        float t = 0; // 记录当前时间流
        int position = Microphone.GetPosition(null); // 记录开始麦克风的音频流位置
        int lastPosition = 0; // 记录上次麦克风的音频流位置

        const float waitTime = 0.04f; // 每隔40ms发送音频
        const int Maxlength = 1080; // 16k 采样率，换算的最大发送长度1280，但是不稳定，640会数据堆积，所以减少一点

        while (isRecording && socket.State == WebSocketState.Open) { // 有录音数据，且服务器保持连接 todo 不稳定
            if (position >= RecordedClip.samples) {
                if (Microphone.IsRecording(null)) {
                    isRecording = false;
                    yield return new WaitForSeconds(0.02f);
                    isRecording = true;
                }
                else {
                    SendOptionOBJ.SendMessage("printTipsInfo", "当前麦克风没有录音，请重新开启语音识别！");
                    isRecording = false;
                    break;
                }
            }

            t += waitTime;
            yield return new WaitForSecondsRealtime(waitTime); // 等待录音40ms

            if (Microphone.IsRecording(null)) // 如果正在录音
                position = Microphone.GetPosition(null); // 更新当前录音位置

            if (position <= lastPosition) { // 如果当前录音位置小于等于上次录音位置
                if (!isRecording && isSpeaking) {
                    isSpeaking = false;
                    endSpeech();
                }
                else {
                    if (isSpeaking) {
                        SendOptionOBJ.SendMessage("printTipsInfo", "麦克风录音异常终止，请重新开启语音识别！");
                        isSpeaking = false;
                        endSpeech();
                    }
                }
                break;
                // restartVoice();
            }

            int length =
                position - lastPosition > Maxlength ? Maxlength : position - lastPosition; // 截断录音长度，确保在640-->1280以内
            byte[] data = getFragmentAudioStream(lastPosition, length, RecordedClip);

            sendAudioData(data);
            lastPosition += length; // 更新上次录音的位置
        }

        if (socket.State != WebSocketState.Open && isSpeaking) {
            SendOptionOBJ.SendMessage("printTipsInfo", "当前与语音识别服务器断连!请重新开启！");
            isSpeaking = false;
            endSpeech();
        }
        else if (!isRecording) {
            sendEndMessage(socket, ct); // 告知后台识别结束
        }
    }

    async void connectAudioWebSocketWebSocket() {
        using (audioWebSocket = new ClientWebSocket()) { // 初始化 ClientWebSocket
            CancellationToken ct = new CancellationToken();
            Uri url = new Uri(getUrl("wss://asr.cloud.tencent.com/asr/v2/" + AppId + "?")); // pp: share we make this in the config file in global?
            await audioWebSocket.ConnectAsync(url, ct); // 握手连接

            StartCoroutine(sendAudioStream(audioWebSocket, ct)); // 开始传输音频数据

            while (audioWebSocket.State == WebSocketState.Open) { // 保持连接时，进行循环
                var result = new byte[4096];
                try {
                    await audioWebSocket.ReceiveAsync(new ArraySegment<byte>(result), ct); // 接受数据
                }
                catch (Exception e) {
                    Console.WriteLine(e);
                    throw;
                }

                List<byte> list = new List<byte>(result);
                while (list[list.Count - 1] == 0x00)
                    list.RemoveAt(list.Count - 1); // 去除空字节

                string str = Encoding.UTF8.GetString(list.ToArray()); // 获得请求结果
                if (string.IsNullOrEmpty(str)) {
                    return;
                }

                getData data = JsonUtility.FromJson<getData>(str);
                string nowText = getWordResult(data);

                string nowOption = getDialogAgentAction(nowText); // pp added: call dialogue agent to get a command (action).

                sendOption(nowOption);

                int status = data.code;
                if (status != 0) { // 返回码不是0，错误
                    audioWebSocket.Abort();
                    SendOptionOBJ.SendMessage("printTipsInfo", "语音识别超时！请尝试重新开启语音！");
                    if (isSpeaking) {
                        isSpeaking = false;
                        endSpeech();
                    }

                    break;
                }
            }
        }
    }

    // pp added: call dialogue agent by API and get an action as a return
    string getDialogAgentAction(string nowText) {

    }

    public void sendOption(string option) {
        foreach (var ins in optionList) {
            if (option.Contains(ins)) {
                SendOptionOBJ.SendMessage(ins);
                break;
            }
        }
    }

//    public void sendOption(string option) {
//        foreach (var ins in myInstruction) {
//            if (option.Contains(ins.Key)) {
//                SendOptionOBJ.SendMessage(ins.Value);
//                break;
//            }
//        }
//    }

    [Serializable]
    public class getData { // 反序列化Json结构
        [Serializable]
        public class Result {
            [Serializable]
            public class WordArray {
                private string word;
                private int start_time;
                private int end_time;
                private int stable_flag;
            }

            public WordArray array;
            public string slice_type; // 识别结果类型
            public string index; // 当前一段话结果在整个音频流中的序号
            public string start_time; // 当前一段话结果在整个音频流中的起始时间
            public string end_time; // 当前一段话结果在整个音频流中的结束时间
            public string voice_text_str; // 当前一段话文本结果，编码为 UTF8
            public int word_size; // 当前一段话的词结果个数
        }

        public int code; // 状态码，0代表正常，非0值表示发生错误
        public string message; // 错误说明，发生错误时显示这个错误发生的具体原因，随着业务发展或体验优化，此文本可能会经常保持变更或更新
        public string voice_id; // 音频流唯一 id，由客户端在握手阶段生成并赋值在调用参数中
        public string message_id; // 本 message 唯一 id
        public Result result; // 最新语音识别结果
        public int final; // 该字段返回1时表示音频流全部识别结束
    }


    string getWordResult(getData data) { // 拼接获得结果字符串
        StringBuilder stringBuilder = new StringBuilder();
        string ans = data.result.voice_text_str;
        string status = data.result.slice_type;
        if (status == "2") {
            stringBuilder.Append(ans);
            Debug.Log("识别结果" + ans);
        }

        return stringBuilder.ToString();
    }
}