## 调用方法
```
stitchimage.exe 汇总目录路径
```
例:
```
stitchimage.exe D:\TestData
```
## 目录要求
汇总目录内的结构应如下，且保证每个目录下图片数量一致
```
InputData
├─ FirstModel
│    ├─ one-xxx.jpg
│    ├─ two-yyy.jpg
│    └─ ...
├─ SecondModel
│    ├─ one-xxx.jpg
│    ├─ two-yyy.jpg
│    └─ ...
```
## 输出路径
汇总目录路径下的 Results 文件夹

## 参数设置
程序路径下的 conf.ini 可设置部分参数

随机打乱模式 (隐藏图片信息)
```
ShuffleMode=True
```