using System.Collections;
using System.Collections.Generic;
using System.IO;
using UnityEngine;
using UnityEngine.UI;
using DG.Tweening;
using TMPro;
using Vuforia;
using vuImage = Vuforia.Image;
using Image = UnityEngine.UI.Image;
using UnityEngine.Android;
using UnityEngine.Networking;
using UnityEngine.Serialization;

public class UploadAndTrans : MonoBehaviour {
    const PixelFormat PIXEL_FORMAT = PixelFormat.RGB888;
    const TextureFormat TEXTURE_FORMAT = TextureFormat.RGB24;
    public RawImage RawImage;
    Texture2D mTexture;
    Texture2D mtexture;
    Texture2D cachedTexture2D; // 在外部创建一个固定大小的Texture2D对象
    bool mFormatRegistered;

    private bool capture;
    private int imageNum = 0;
    private WaitForSeconds upImgWaitTime; // 声明成员变量

    // private string url = "http://124.220.8.170:8888/upload_image";
    private string url = "http://101.43.21.188:5050/upload_image";
    public Transform m_ParObj; // 中心点
    private List<GameObject> m_Child; // 子模块

    public TextMeshProUGUI tipsPrint; // 输出提示信息

    private List<Vector3> initPosition = new List<Vector3>(); // 初始位置
    private List<Vector3> explodePosition = new List<Vector3>(); // 爆炸变化坐标
    private List<Vector3> assemblePosition = new List<Vector3>(); // 拼装前位置

    public Image progressBar; // 进度条填充图
    public TextMeshProUGUI barText; // 进度条信息提示

    private int currentCount = 0; // 当前进度
    public float total = 0; // 总积木块数
    public float percent = 0; // 当前进度
    private float scale = 1f; // 放缩初始比
    private float lerSpeed = 3; // 填充速度

    private string tips; // 提示信息

    private bool isAssemble = false; // 是否在拼装
    private bool isRecover = true; // 是否恢复模型
    private bool isFinish = false;

    private bool needHand = false; // 是否需要手势识别
    private bool myLock = false;

    private AudioSource source; //音效组

    public Sprite[] modelSprites; // 图片数组
    public Image partCar; // 小车当前零件图

    public Sprite[] assembleSprites; // 开始/重复/结算动画的数组
    public Image startImg; // 小车当前零件图

    public Sprite[] handSprites; // 手势图片数组
    public Image handImg; // 手势当前图

    private bool needRestart = false;
    private bool isTracked = false;
    private bool isNeedLastProgress = false;

    public Button need;
    public Button needNot;
    private int lastProgress;
    private const string progressFileName = "progress.txt";
    public Image lastProInfoUI;
    public TextMeshProUGUI lastProgressInfo; // 上次进度提示信息
    private bool getLastProgess = false;

    public void lastProgressInfoUI(string cur, string tot) {
        if (lastProgress != total)
            lastProgressInfo.text = "是否需要加载上次拼装进度：" + cur + " / " + tot;
        else
            lastProgressInfo.text = "上次拼装已完成，这次将重新开始拼装哦~";
    }

    public void needLast() {
        isNeedLastProgress = true;
        if (lastProgress != total) {
            currentCount = lastProgress;
            printTipsInfo("从上次进度" + lastProgress + "，继续拼装");
        }
        else {
            currentCount = 0;
            printTipsInfo("现在让我们重新开始拼装吧~");
        }
        need.gameObject.SetActive(false);
        needNot.gameObject.SetActive(false);
        lastProgressInfo.enabled = false;
        lastProInfoUI.enabled = false;

        getLastProgess = true;

    }

    public void needNotLast() {
        isNeedLastProgress = false;
        currentCount = 0;
        need.gameObject.SetActive(false);
        needNot.gameObject.SetActive(false);
        lastProgressInfo.enabled = false;
        lastProInfoUI.enabled = false;

        getLastProgess = true;
        printTipsInfo("进度清零，现在让我们重新开始拼装吧！");
    }

    void Start() {
        startImg.sprite = assembleSprites[0];
        handImg.sprite = handSprites[0];

        Permission.RequestUserPermission("android.permission.WRITE_EXTERNAL_STORAGE");
        Permission.RequestUserPermission("android.permission.READ_EXTERNAL_STORAGE");
        Permission.RequestUserPermission("android.permission.CAMERA");
        Permission.RequestUserPermission("android.permission.INTERNET");
        Permission.RequestUserPermission("android.permission.RECORD_AUDIO");

        imageNum = 0;

        // Register Vuforia Engine life-cycle callbacks:
        VuforiaApplication.Instance.OnVuforiaStarted += OnVuforiaStarted;
        VuforiaApplication.Instance.OnVuforiaStopped += OnVuforiaStopped;
        if (VuforiaBehaviour.Instance != null)
            VuforiaBehaviour.Instance.World.OnStateUpdated += OnVuforiaUpdated;

        upImgWaitTime = new WaitForSeconds(0.5f);

        m_Child = m_ParObj.GetChild(); // 获取所有子对象
        total = m_Child.Count;
        for (int i = 0; i < m_Child.Count; i++) { // 添加坐标项
            explodePosition.Add(m_Child[i].transform.position);
        }

        lastProgress = LoadProgress(); // 获取上次进度
        lastProgressInfoUI(lastProgress.ToString(), total.ToString());

        trackNo();
        setVal2Explode();

        source = GetComponent<AudioSource>(); //初始化音效组件
    }

    public void trackYes() {
        isTracked = true;
        printTipsInfo("找到目标基座咯，小车就在基座上~");
    }

    public void trackNo() {
        if (isTracked) {
            printTipsInfo("要找到基座才能对小车继续操作哦");
            isTracked = false;
        }
        else {
            isTracked = false;
            printTipsInfo("准备好了吗？找到基座，先来看看模型的样子吧！可以放缩零件查看细节哦~");
        }
    }


    private void mutex(float time) {
        Lock();
        Invoke("unLock", time);
    }

    private void Lock() {
        myLock = true;
    }

    private void unLock() {
        myLock = false;
    }

    void OnDestroy() {
        // Unregister Vuforia Engine life-cycle callbacks:
        if (VuforiaBehaviour.Instance != null)
            VuforiaBehaviour.Instance.World.OnStateUpdated -= OnVuforiaUpdated;

        VuforiaApplication.Instance.OnVuforiaStarted -= OnVuforiaStarted;
        VuforiaApplication.Instance.OnVuforiaStopped -= OnVuforiaStopped;

        if (VuforiaApplication.Instance.IsRunning) {
            // If Vuforia Engine is still running, unregister the camera pixel format to avoid unnecessary overhead
            // Formats can only be registered and unregistered while Vuforia Engine is running
            UnregisterFormat();
        }

        if (mTexture != null)
            Destroy(mTexture);
    }

    void OnVuforiaStarted() { // Called each time the Vuforia Engine is started
        mTexture = new Texture2D(0, 0, TEXTURE_FORMAT, false);
        // A format cannot be registered if Vuforia Engine is not running
        RegisterFormat();
    }

    void OnVuforiaStopped() { // Called each time the Vuforia Engine is stopped
        // A format cannot be unregistered after OnVuforiaStopped
        UnregisterFormat();
        if (mTexture != null)
            Destroy(mTexture);
    }

    void OnVuforiaUpdated() { // Called each time the Vuforia Engine state is updated
        var image = VuforiaBehaviour.Instance.CameraDevice.GetCameraImage(PIXEL_FORMAT);

        // There can be a delay of several frames until the camera image becomes available
        if (vuImage.IsNullOrEmpty(image))
            return;

        // Override the current texture by copying into it the camera image flipped on the Y axis
        // The texture is resized to match the camera image size
        image.CopyToTexture(mTexture, true);

        RawImage.texture = mTexture;
        RawImage.material.mainTexture = mTexture;

        InputSave(); // 新增上传图片
    }

    void RegisterFormat() { // Register the camera pixel format
        // Vuforia Engine has started, now register camera image format
        var success = VuforiaBehaviour.Instance.CameraDevice.SetFrameFormat(PIXEL_FORMAT, true);
        if (success) {
            mFormatRegistered = true;
        }
        else {
            mFormatRegistered = false;
        }
    }

    void UnregisterFormat() { // Unregister the camera pixel format
        VuforiaBehaviour.Instance.CameraDevice.SetFrameFormat(PIXEL_FORMAT, false);
        mFormatRegistered = false;
    }

    public void changeHand() {
        if (needHand == true) { // 关闭手势
            needHand = false;
            handImg.sprite = handSprites[0];
            printTipsInfo("关闭手势交互");
        }
        else { // 打开手势
            needHand = true;
            handImg.sprite = handSprites[1];
            printTipsInfo("开始手势交互");
        }
    }

    // 按钮回调 新增存储图片
    public void InputSave() {
        if (needHand && !capture) { // 屏幕渲染
            capture = true;
            StartCoroutine(CaptureAndSave02()); // todo debug时关闭
        }
    }

    public IEnumerator CaptureAndSave02() {
        if (capture && needHand) {
            //等待屏幕渲染结束后获取屏幕像素信息
            yield return new WaitForEndOfFrame();
            cachedTexture2D = new Texture2D(RawImage.texture.width / 5, RawImage.texture.height / 5,
                TextureFormat.RGB24, false);
            TextureToTexture2D(RawImage.texture, ref cachedTexture2D);

            // 将图片转为byte直接传给服务器
            byte[] imageByte = cachedTexture2D.EncodeToPNG();
            WWWForm form = new WWWForm();
            form.AddBinaryData("file", imageByte, (imageNum++) + ".png", "image/png");

            using (UnityWebRequest www = UnityWebRequest.Post(url, form)) {
                yield return www.SendWebRequest();
                if (www.isNetworkError || www.isHttpError) {
                    printTipsInfo("当前与手势服务器连接失败，请重试！");
                }
                else {
                    string result = www.downloadHandler.text;
                    optionCase(result);
                }
            }

            yield return upImgWaitTime; // update: 0.5s 传一张照片
            capture = false;
        }
    }

    private void TextureToTexture2D(Texture texture, ref Texture2D cachedTexture2D) { // 运行模式下Texture转换成Texture2D
        RenderTexture
            renderTexture =
                RenderTexture.GetTemporary(texture.width / 5, texture.height / 5, 24); // todo 改成24位深度是否能带来加速
        Graphics.Blit(texture, renderTexture);

        RenderTexture.active = renderTexture;
        cachedTexture2D.ReadPixels(new Rect(0, 0, renderTexture.width, renderTexture.height), 0, 0);
        cachedTexture2D.Apply();

        RenderTexture.ReleaseTemporary(renderTexture);
    }

    private void optionCase(string op) { // 向积木模块发出控制消息
        if (op == "again") {
            startAssemble();
        }
        else if (op == "advance") {
            NextStep();
        }
        else if (op == "back") {
            FrontStep();
        }
        else if (op == "explode") {
            Explode();
        }
        else if (op == "reclaim") {
            Recover();
        }
        else if (op == "finish") {
            FinishedVideo();
        }
    }

    private void Update() { // 每帧都刷新：更新进度条
        BarFiller();
        showInfo();
        if (Input.GetKeyDown(KeyCode.Escape)) {
            SaveAndQuit();
        }
    }

    public static void SaveProgress(int progress) {
        string filePath = Path.Combine(Application.persistentDataPath, progressFileName);
        File.WriteAllText(filePath, progress.ToString());
    }

    public static int LoadProgress() {
        string filePath = Path.Combine(Application.persistentDataPath, progressFileName);
        if (File.Exists(filePath)) {
            string progressString = File.ReadAllText(filePath);
            if (int.TryParse(progressString, out int progress)) {
                return progress;
            }
        }

        return 0; // 默认进度为0
    }

    public void SaveAndQuit() {
        // 保存进度
        SaveProgress(currentCount);

        // 退出游戏
        Application.Quit();
    }

    public void showPartImg(int index) {
        partCar.sprite = modelSprites[index];
    }

    private void setVal2Explode() { // 爆炸位移坐标
        explodePosition[0] = new Vector3(0, -0.010f, 0.020f);
        explodePosition[1] = new Vector3(0.040f, -0.010f, 0.020f);
        explodePosition[2] = new Vector3(-0.040f, -0.010f, 0.020f);

        explodePosition[3] = new Vector3(0, -0.010f, -0.020f);
        explodePosition[4] = new Vector3(0.040f, -0.010f, -0.020f);
        explodePosition[5] = new Vector3(-0.040f, -0.010f, -0.020f);

        explodePosition[6] = new Vector3(0, 0.020f, 0);
        explodePosition[7] = new Vector3(0, 0.020f, 0.020f);

        explodePosition[8] = new Vector3(0, 0.040f, 0);
        explodePosition[9] = new Vector3(0, 0.040f, -0.010f);

        explodePosition[10] = new Vector3(-0.040f, 0.050f, 0);
        explodePosition[11] = new Vector3(0.040f, 0.050f, 0);
        explodePosition[12] = new Vector3(-0.040f, 0.050f, -0.010f);
        explodePosition[13] = new Vector3(0.040f, 0.050f, -0.010f);

        explodePosition[14] = new Vector3(0, 0.050f, 0.010f);
        explodePosition[15] = new Vector3(0, 0.060f, 0);
        explodePosition[16] = new Vector3(0, 0.060f, 0.010f);

        explodePosition[17] = new Vector3(0, 0.070f, 0);
        explodePosition[18] = new Vector3(0, 0.080f, 0);
    }

    // private void setVal2Explode() { // debug
    //     explodePosition[0] = new Vector3(0, 0, 20);
    //     explodePosition[1] = new Vector3(40, 0, 20);
    //     explodePosition[2] = new Vector3(-40f, 0, 20);
    //
    //     explodePosition[3] = new Vector3(0, 0, -20);
    //     explodePosition[4] = new Vector3(40f, 0, -20);
    //     explodePosition[5] = new Vector3(-40f, 0, -20);
    //
    //     explodePosition[6] = new Vector3(0, 20f, 0);
    //     explodePosition[7] = new Vector3(0, 20f, 20f);
    //
    //     explodePosition[8] = new Vector3(0, 40f, 0);
    //     explodePosition[9] = new Vector3(0, 40f, -10f);
    //
    //     explodePosition[10] = new Vector3(-40f, 50f, 0);
    //     explodePosition[11] = new Vector3(40f, 50f, 0);
    //     explodePosition[12] = new Vector3(-40f, 50f, -10f);
    //     explodePosition[13] = new Vector3(40f, 50f, -10f);
    //
    //     explodePosition[14] = new Vector3(0, 50f, 10f);
    //     explodePosition[15] = new Vector3(0, 60f, 0);
    //     explodePosition[16] = new Vector3(0, 60f, 10f);
    //
    //     explodePosition[17] = new Vector3(0, 70f, 0);
    //     explodePosition[18] = new Vector3(0, 80f, 0);
    // }

    private void StartVedio() { // 开始动画
        assemblePosition.Clear();
        mutex(0.5f);
        for (int i = 0; i < m_Child.Count; i++) { // 板块爆炸
            assemblePosition.Add(new Vector3(
                initPosition[i].x + explodePosition[i].x * 20,
                initPosition[i].y + explodePosition[i].y * 20,
                initPosition[i].z + explodePosition[i].z * 20)); // 获取无穷远处坐标
            m_Child[i].transform.DOMove(assemblePosition[i], 0.5f, false); // 移动
        }
    }

    private void recoverLastProgress() {
        for (int i = 0; i < currentCount; ++i) {
            m_Child[i].SetActive(true);
        }
    }

    public void startAssemble() { // 开始拼装
        if (isTracked) {
            if (getLastProgess) {
                if (isNeedLastProgress) { // 加载进度
                    if (!isAssemble) { // 没有拼装，进入拼装
                        startImg.sprite = assembleSprites[1];

                        if (!isRecover) { // 拼装时保证模型恢复
                            Recover();
                            Invoke("getInitPosition", 1); // 获得拼装前的初始位置，防止读错了
                            Invoke("StartVedio", 1.1f); // 
                            Invoke("hideBlocks", 2); // 3秒后调用hideBlocks()，只调用一次，隐藏积木块 
                            Invoke("recoverLastProgress", 2.1f);
                        }
                        else {
                            getInitPosition(); // 获得拼装前的初始位置
                            StartVedio(); // 播放拼装爆炸动画
                            Invoke("hideBlocks", 0.5f); // 1秒后调用hideBlocks()，只调用一次，隐藏积木块 
                            Invoke("recoverLastProgress", 0.6f);
                        }

                        isAssemble = true; // 逻辑优先级
                        printTipsInfo("跟上我的脚步，一步一步拼出你喜欢的积木吧！");
                    }

                    if (!isAssemble && currentCount == total) {
                        if (needRestart) {
                            currentCount = 0;
                            needRestart = false;
                            startAssemble();
                        }
                        else {
                            printTipsInfo("如果需要重新拼装，请再进行一次开始操作哦");
                            needRestart = true;
                        }
                    }
                    else { // 拼装过程，重新开始 --> 重新显示当前步骤
                        ReShow();
                    }
                }
                else { // 不加载进度
                    if (!isAssemble && currentCount == 0) { // 没有拼装，进入拼装
                        startImg.sprite = assembleSprites[1];

                        if (!isRecover) { // 拼装时保证模型恢复
                            Recover();
                            Invoke("getInitPosition", 1); // 获得拼装前的初始位置，防止读错了
                            Invoke("StartVedio", 1.1f); // 
                            Invoke("hideBlocks", 2); // 3秒后调用hideBlocks()，只调用一次，隐藏积木块 
                        }
                        else {
                            getInitPosition(); // 获得拼装前的初始位置
                            StartVedio(); // 播放拼装爆炸动画
                            Invoke("hideBlocks", 0.5f); // 1秒后调用hideBlocks()，只调用一次，隐藏积木块 
                        }

                        isAssemble = true; // 逻辑优先级
                        printTipsInfo("跟上我的脚步，一步一步拼出你喜欢的积木吧！");
                    }

                    if (!isAssemble && currentCount == total) {
                        if (needRestart) {
                            currentCount = 0;
                            needRestart = false;
                            startAssemble();
                        }
                        else {
                            printTipsInfo("如果需要重新拼装，请再进行一次开始操作哦");
                            needRestart = true;
                        }
                    }
                    else { // 拼装过程，重新开始 --> 重新显示当前步骤
                        ReShow();
                    }
                }
            }
            else {
                printTipsInfo("需要选择是否加载上次进度才能开始拼装哦");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    private void hideBlocks() { // 隐藏积木块
        mutex(0.01f);
        for (int i = 0; i < m_Child.Count; i++) { // 初始化不显示
            m_Child[i].SetActive(false);
            m_Child[i].transform.DOMove(initPosition[i], 0.01f, false); // 移动
        }
    }

    private void showInfo() { // 进度条信息
        percent = currentCount / total * 100;
        tips = "当前拼装进度：" + percent.ToString("0.00") + " %";
        barText.text = tips;
    }

    private void BarFiller() { // 填充进度条
        progressBar.fillAmount = Mathf.Lerp(progressBar.fillAmount, currentCount / total, lerSpeed * Time.deltaTime);
    }

    public void printTipsInfo(string tips) {
        tipsPrint.text = tips;
    }

    public void showCarPartAndAdvance() {
        mutex(1.5f);
        m_Child[currentCount].SetActive(true);
        source.Play(); //播放音效

        Material[] myMaterials = m_Child[currentCount].GetComponent<MeshRenderer>().materials;
        foreach (Material m in myMaterials) {
            Tweener twe = m.DOColor(Color.red, 1.5f).From(); // 红色高亮渐变，连续点击会导致色彩印上
        }

        currentCount += 1;
    }

    public void NextStep() { // 拼装下一步
        if (isTracked) {
            if (isAssemble && !myLock) {
                showPartImg(currentCount);
                if (currentCount < m_Child.Count) {
                    showCarPartAndAdvance();
                    printTipsInfo("继续：第 " + currentCount + " 步拼装演示");
                }

                if (currentCount == m_Child.Count) { // 拼到最后一步了
                    isAssemble = false;
                    startImg.sprite = assembleSprites[2];
                    printTipsInfo("恭喜，你已经搭建出你想要的积木了！");
                }

                Update();
            }
            else if (!isAssemble && currentCount == total) {
                showPartImg(currentCount);
                printTipsInfo("恭喜，你已经搭建出你想要的积木了！");
            }
            else if (!myLock) {
                printTipsInfo("开始拼装就可以查看步骤啦~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void FrontStep() { // 拼装上一步
        if (isTracked) {
            if (isAssemble && !myLock) { // 正在拼装
                if (currentCount > 1) { // 连续减两步
                    currentCount -= 1; // 隐藏当前步
                    m_Child[currentCount].SetActive(false);

                    currentCount -= 1; // 隐藏上一步
                    m_Child[currentCount].SetActive(false);
                    showCarPartAndAdvance();

                    printTipsInfo("返回：第 " + currentCount + " 步拼装演示");
                }
                else if (currentCount == 1) { // 第一步重新显示
                    ReShow();
                }
                else if (currentCount == 0) {
                    printTipsInfo("当前还没有开始拼装");
                }

                Update();
            }
            else if (!isAssemble && currentCount == total) {
                printTipsInfo("恭喜，你已经搭建出你想要的积木了！");
            }
            else if (!myLock) {
                printTipsInfo("开始拼装就可以查看步骤啦~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void ReShow() { // 重新显示当前步骤
        if (isTracked) {
            if (isAssemble && !myLock) {
                if (currentCount == 0) {
                    printTipsInfo("当前还没有开始拼装");
                }
                else if (currentCount > 0) {
                    m_Child[currentCount].SetActive(false);
                    currentCount -= 1;

                    m_Child[currentCount].SetActive(false);
                    showCarPartAndAdvance();
                    printTipsInfo("重显：第 " + currentCount + " 步拼装演示");
                }
            }
            else if (!isAssemble && currentCount == total) {
                printTipsInfo("恭喜，你已经搭建出你想要的积木了！");
            }
            else if (!myLock) {
                printTipsInfo("开始拼装就可以查看步骤啦~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void Shrink() { // 缩小
        if (isTracked) {
            if (scale <= 0.5f) { // 最低小到0.5
                printTipsInfo("最低就缩小到 0.5 倍啦~");
                return;
            }

            mutex(1f);
            scale = scale - 0.1f;
            if (!myLock) {
                for (int i = 0; i < m_Child.Count; i++) {
                    m_Child[i].transform.DOScale(scale, 1f);
                }

                printTipsInfo("缩小积木到 " + scale.ToString("0.0") + " 倍");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void Enlarge() { // 放大
        if (isTracked) {
            if (scale >= 2.0f) { // 最多放大两倍
                printTipsInfo("最多就放大到 2 倍啦~");
                return;
            }

            mutex(1f);
            if (!myLock) {
                scale = scale + 0.1f;
                for (int i = 0; i < m_Child.Count; i++) {
                    m_Child[i].transform.DOScale(scale, 1f);
                }

                printTipsInfo("放大积木到 " + scale.ToString("0.0") + " 倍");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void LeftRotate() { // 左旋
        mutex(0.5f);
        m_ParObj.transform.DORotate(new Vector3(0, 60, 0), 0.5f, RotateMode.WorldAxisAdd);
        printTipsInfo("左旋模型");
    }

    public void RightRotate() { // 右旋
        mutex(0.5f);
        m_ParObj.transform.DORotate(new Vector3(0, -60, 0), 0.5f, RotateMode.WorldAxisAdd);
        printTipsInfo("右旋模型");
    }

    private void getInitPosition() { // 获取各零件当前状态的坐标
        initPosition.Clear(); // 防止内存泄漏
        for (int i = 0; i < m_Child.Count; i++) { // 获取爆炸前瞬间的初始坐标
            initPosition.Add(m_Child[i].transform.position);
        }
    }

    public void Explode() { // 爆炸特效
        if (isTracked) {
            if (!isAssemble) {
                if (isRecover && !myLock) {
                    getInitPosition();
                    mutex(1f);
                    for (int i = 0; i < m_Child.Count; i++) { // 爆炸坐标更变
                        m_Child[i].transform.DOMove(new Vector3(
                            initPosition[i].x + explodePosition[i].x,
                            initPosition[i].y + explodePosition[i].y,
                            initPosition[i].z + explodePosition[i].z
                        ), 1f, false);
                    }

                    isRecover = false;
                    printTipsInfo("查看模型细节");
                }
                else if (isRecover && myLock) {
                    printTipsInfo("模型正在恢复，请给它一点时间哦~");
                }
                else {
                    printTipsInfo("已经在查看细节啦~");
                }
            }
            else {
                printTipsInfo("当前正处于拼装的过程，不能查看细节哦~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void Recover() { // 爆炸特效收回
        if (isTracked) {
            if (!isRecover) { // 注意逻辑判定优先级
                if (!isAssemble && !myLock) {
                    mutex(1f);
                    for (int i = 0; i < initPosition.Count; i++) { // 恢复到爆炸初始前瞬间的坐标
                        m_Child[i].transform.DOMove(initPosition[i], 1f, false);
                    }

                    isRecover = true;
                    printTipsInfo("模型展示恢复");
                }
                else if (!isAssemble && myLock) {
                    printTipsInfo("模型正在展开，请给它一点时间哦~");
                }
                else {
                    printTipsInfo("当前正处于拼装的过程，模型已经恢复啦");
                }
            }
            else {
                printTipsInfo("模型已经恢复啦~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    public void FinishedVideo() {
        if (isTracked) {
            if (!isAssemble && currentCount == total && !isFinish) {
                changeFinish();
                finishedTurn90();
                mutex(8f);
                Invoke("finishedMoveHead", 0.5f);
                Invoke("finishedTurn180", 3.5f);
                Invoke("finishedMoveBack", 4f);
                Invoke("finishedTurn90", 7f);
                Invoke("changeFinish", 8f);

                printTipsInfo("小车跑起来咯，谢谢你给它赋予了数字生命哦~");
            }
            else if (isAssemble) {
                printTipsInfo("拼完之后小车才能动哦~");
            }
            else if (!isAssemble && currentCount != total) {
                printTipsInfo("开始拼装后才能给小车数字生命哦~");
            }
            else if (!isAssemble && isFinish) {
                printTipsInfo("小车正在移动~");
            }
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }

    private void changeFinish() {
        isFinish = !isFinish;
    }

    private void finishedTurn90() {
        m_ParObj.transform.DORotate(new Vector3(0, 90, 0), 0.5f, RotateMode.WorldAxisAdd);
    }

    private void finishedTurn180() {
        m_ParObj.transform.DORotate(new Vector3(0, 180, 0), 0.5f, RotateMode.WorldAxisAdd);
    }

    private void finishedMoveHead() {
        m_ParObj.transform.DOMove(new Vector3(-0.2f, -0, 0), 3f).SetRelative();
    }

    private void finishedMoveBack() {
        m_ParObj.transform.DOMove(new Vector3(0.2f, 0, 0), 3f).SetRelative();
    }

    public void clickBoomOrRecover() {
        if (isRecover)
            Explode();
        else
            Recover();
    }

    public void changeStartBuntton() {
        if (isTracked) {
            if (!isAssemble) { // 没有拼装
                if (currentCount == total) { // 已经拼完
                    if (isNeedLastProgress) { // 如果上一次加载的对象是拼好了，则可以重新开始
                        currentCount = 0;
                        startAssemble();
                    }
                    else {
                        FinishedVideo();
                    }
                }
                else
                    startAssemble();
            }
            else // 在拼装
                ReShow();
        }
        else {
            printTipsInfo("需要找到基座，才能继续对小车进行操作哦");
        }
    }
}