from PIL import Image
import numpy as np
import paddle.fluid as fluid
from paddle.fluid.dygraph.nn import Linear,Conv2D,Pool2D
import cv2
import random
import json
import gzip

# img_path = "example_0.png"
# im = cv2.imread(img_path,0)
# print(im.shape)
# im1 = cv2.resize(im,(28,28))
# print(im1.shape,im1)
# im2 = 1 - im/127.5
# print("im2",im2)

def load_image(img_path):
    img_path = "example_0.png"
    im = cv2.imread(img_path, 0)
    # print(im.shape)
    im1 = cv2.resize(im, (28, 28))
    # print(im1.shape, im1)
    im1 = im1.reshape(1,-1).astype(np.float32)
    im2 = 2 - im1 / 127.5
    print("im2", im2.shape,im2)
    return im2

    # im = Image.open(img_path).convert('L')
    # im = im.resize((28,28),Image.ANTIALIAS)
    # print("shape",type(im))
    # im = np.array(im).reshape(1,-1).astype(np.float32)
    # print("shape", im.shape)
    # print("im1",im)
    # # im = 2 -im/127.5
    # im = 1 - im/127.5
    # print("im2", im)
    # return im

def load_data(mode='train'):
    # 数据文件
    datafile = 'mnist.json.gz'
    print('loading mnist dataset from {} ......'.format(datafile))
    data = json.load(gzip.open(datafile))
    # 读取到的数据可以直接区分训练集，验证集，测试集
    train_set, val_set, eval_set = data

    # 数据集相关参数，图片高度IMG_ROWS, 图片宽度IMG_COLS
    IMG_ROWS = 28
    IMG_COLS = 28
    # 获得数据
    if mode == 'train':
        imgs = train_set[0]
        labels = train_set[1]
    elif mode == 'valid':
        imgs = val_set[0]
        labels = val_set[1]
    elif mode == 'eval':
        imgs = eval_set[0]
        labels = eval_set[1]
    else:
        raise Exception("mode can only be one of ['train', 'valid', 'eval']")

    imgs_length = len(imgs)

    assert len(imgs) == len(labels), \
        "length of train_imgs({}) should be the same as train_labels({})".format(
            len(imgs), len(labels))

    index_list = list(range(imgs_length))

    # 读入数据时用到的batchsize
    BATCHSIZE = 100

    # 定义数据生成器
    def data_generator():
        # if mode == 'train':
        #     # 训练模式下，将训练数据打乱
        #     random.shuffle(index_list)
        imgs_list = []
        labels_list = []

        for i in index_list:
            img = np.reshape(imgs[i], [1, IMG_ROWS, IMG_COLS]).astype('float32')
            # img = np.array(imgs[i]).astype('float32')

            # label = np.reshape(labels[i], [1]).astype('float32')
            label = np.reshape(labels[i],[1]).astype('int64')
            imgs_list.append(img)
            labels_list.append(label)
            if len(imgs_list) == BATCHSIZE:
                # 产生一个batch的数据并返回
                yield np.array(imgs_list), np.array(labels_list)
                # 清空数据读取列表
                imgs_list = []
                labels_list = []

        # 如果剩余数据的数目小于BATCHSIZE，
        # 则剩余数据一起构成一个大小为len(imgs_list)的mini-batch
        if len(imgs_list) > 0:
            yield np.array(imgs_list), np.array(labels_list)

    return data_generator

class MNIST(fluid.dygraph.Layer):
    def __init__(self,name_scope):
        super(MNIST,self).__init__(name_scope)
        name_scope = self.full_name()
        # 定义卷积层，输出特征通道num_filters设置为20，卷积核的大小filter_size为5，卷积步长stride=1，padding=2
        # 激活函数使用relu
        self.conv1 = Conv2D(num_channels=1,num_filters=20, filter_size=5, stride=1, padding=2, act='relu')
        # 定义池化层，池化核pool_size=2，池化步长为2，选择最大池化方式
        self.pool1 = Pool2D( pool_size=2, pool_stride=2, pool_type='max')
        # 定义卷积层，输出特征通道num_filters设置为20，卷积核的大小filter_size为5，卷积步长stride=1，padding=2
        self.conv2 = Conv2D(num_channels=20, num_filters=20, filter_size=5, stride=1, padding=2, act='relu')
        # 定义池化层，池化核pool_size=2，池化步长为2，选择最大池化方式
        self.pool2 = Pool2D(pool_size=2, pool_stride=2, pool_type='max')

        # self.linear = Linear(20*7*7, 1, act=None)
        self.linear = Linear(20*7*7, 10, act='softmax')

    def forward(self, inputs,label = None,check_shape = False,check_content=False):
         outputs1 = self.conv1(inputs)
         outputs2 = self.pool1(outputs1)
         outputs3 = self.conv2(outputs2)
         outputs4 = self.pool2(outputs3)
         outputs4 = outputs4.numpy()
         outputs4 = np.reshape(outputs4,[100,-1])
         outputs4 = fluid.dygraph.to_variable(outputs4)
         outputs5 = self.linear(outputs4)

         if check_shape:
             # 打印每层网络设置的超参数-卷积核尺寸，卷积步长，卷积padding，池化核尺寸
             print("\n########## print network layer's superparams ##############")
             print("\n########## print network layer's superparams ##############")
             print("conv1-- kernel_size:{}, padding:{}, stride:{}".format(self.conv1.weight.shape, self.conv1._padding, self.conv1._stride))
             print("conv2-- kernel_size:{}, padding:{}, stride:{}".format(self.conv2.weight.shape, self.conv2._padding, self.conv2._stride))
             print("pool1-- pool_type:{}, pool_size:{}, pool_stride:{}".format(self.pool1._pool_type, self.pool1._pool_size, self.pool1._pool_stride))
             print("pool2-- pool_type:{}, poo2_size:{}, pool_stride:{}".format(self.pool2._pool_type, self.pool2._pool_size, self.pool2._pool_stride))
             print("fc-- weight_size:{}, bias_size_{}, activation:{}".format(self.linear.weight.shape, self.linear.bias.shape, self.linear._act))

             # 打印每层的输出尺寸
             print("\n########## print shape of features of every layer ###############")
             print("inputs_shape: {}".format(inputs.shape))
             print("outputs1_shape: {}".format(outputs1.shape))
             print("outputs2_shape: {}".format(outputs2.shape))
             print("outputs3_shape: {}".format(outputs3.shape))
             print("outputs4_shape: {}".format(outputs4.shape))
             print("outputs5_shape: {}".format(outputs5.shape))
         # 选择是否打印训练过程中的参数和输出内容，可用于训练过程中的调试
         if check_content:
             print("\n########## print convolution layer's kernel ###############")
             print("conv1 params -- kernel weights:", self.conv1.weight[0][0])
             print("conv2 params -- kernel weights:", self.conv2.weight[0][0])

             # 创建随机数，随机打印某一个通道的输出值
             idx1 = np.random.randint(0, outputs1.shape[1])
             idx2 = np.random.randint(0, outputs3.shape[1])
             # 打印卷积-池化后的结果，仅打印batch中第一个图像对应的特征
             print("\nThe {}th channel of conv1 layer: ".format(idx1), outputs1[0][idx1])
             print("The {}th channel of conv2 layer: ".format(idx2), outputs3[0][idx2])
             print("The output of last layer:", outputs5[0], '\n')


         if label is not None:
             acc = fluid.layers.accuracy(input=outputs5,label=label)
             return outputs5,acc
         else:
            return outputs5
##单个图片
# with fluid.dygraph.guard():
#     # 预测单张图片
#     # model = MNIST("mnist")
#     # img_path = "example_0.png"
#     # params_file_path = 'mnist'
#     # model_dict,_ = fluid.load_dygraph("mnist")
#     # model.load_dict(model_dict)
#     # model.eval()
#     # tensor_img = load_image(img_path)
#     # print("tensor_img",tensor_img)
#     # result = model.forward(fluid.dygraph.to_variable(tensor_img))
#     # print("predict num is : {}".format(result.numpy().astype('int32')))
#     print('start evaluation ......')
#     model = MNIST('mnist')
#     model_static_dict,_ = fluid.dygraph.load_dygraph('mnist')
#     model.load_dict(model_static_dict)
#     model.eval()
#     eval_loader = load_data('eval')
#     acc_set = []
#     avg_loss_set = []
#     for batch_id,data in enumerate(eval_loader()):
#         x_data,y_data = data
#         img = fluid.dygraph.to_variable(x_data)
#         label = fluid.dygraph.to_variable(y_data)
#         prediction,acc = model.forward(img,label)
#         loss  = fluid.layers.cross_entropy(prediction,label)
#         avg_loss = fluid.layers.mean(loss)
#         acc_set.append(float(acc.numpy()))
#         avg_loss_set.append(float(avg_loss.numpy()))
#     acc_val_mean = np.array(acc_set).mean()
#     avg_loss_val_mean = np.array(avg_loss_set).mean()
#
#     print('loss={}, acc={}'.format(avg_loss_val_mean, acc_val_mean))



##在验证集的结果

# with fluid.dygraph.guard():
#     print('start evaluation .......')
#     # 加载模型参数
#     model = MNIST("mnist")
#     model_state_dict, _ = fluid.load_dygraph('mnist')
#     model.load_dict(model_state_dict)
#
#     model.eval()
#     eval_loader = load_data('eval')
#
#     acc_set = []
#     avg_loss_set = []
#     for batch_id, data in enumerate(eval_loader()):
#         x_data, y_data = data
#         img = fluid.dygraph.to_variable(x_data)
#         label = fluid.dygraph.to_variable(y_data)
#         prediction, acc = model(img, label)
#         loss = fluid.layers.cross_entropy(input=prediction, label=label)
#         avg_loss = fluid.layers.mean(loss)
#         acc_set.append(float(acc.numpy()))
#         avg_loss_set.append(float(avg_loss.numpy()))
#
#     # 计算多个batch的平均损失和准确率
#     acc_val_mean = np.array(acc_set).mean()
#     avg_loss_val_mean = np.array(avg_loss_set).mean()
#
#     print('loss={}, acc={}'.format(avg_loss_val_mean, acc_val_mean))



# params_path = "./checkpoint/mnist_epoch0"
params_path = "checkpoint/mnist_epoch0"
place = fluid.CPUPlace()

with fluid.dygraph.guard(place):
    params_dict, opt_dict = fluid.load_dygraph(params_path)
    model = MNIST("mnist")
    model.set_dict(params_dict)
    train_loader = load_data('train')

    # 异步代码二 定义DataLoader对象用于加载Python生成器产生的数据
    data_loader = fluid.io.DataLoader.from_generator(capacity=5, return_list=True)
    # 异步代码三 设置数据生成器
    data_loader.set_batch_generator(train_loader, places=place)

    # linears= Linear(784,1,dtype='float32')
    # optimizer=fluid.optimizer.SGDOptimizer(learning_rate=0.01,parameter_list=model.parameters(),regularization=fluid.regularizer.L2Decay(regularization_coeff=0.1))
    EPOCH_NUM = 5
    iter = 0
    total_steps = (int(60000/100)+1)*EPOCH_NUM
    lr = fluid.dygraph.PolynomialDecay(0.01,total_steps,0.001)
    optimizer = fluid.optimizer.AdamOptimizer(learning_rate=lr,parameter_list=model.parameters())
    optimizer.set_dict(opt_dict)
    for epoch_id in range(1,EPOCH_NUM):
        # for batch_id,data in enumerate(data_generator("train")):
        for batch_id,data in enumerate(train_loader()):

            image_data,label_data = data
            # print("shape",image_data.shape,label_data.shape)
            image = fluid.dygraph.to_variable(image_data)
            label = fluid.dygraph.to_variable(label_data)

            if batch_id == 0 and epoch_id==0:
                predict, avg_acc = model.forward(image, label,check_shape=True,check_content=False)
            elif batch_id == 401:
                predict, avg_acc = model.forward(image, label, check_shape=False, check_content=True)
            else:
                predict, avg_acc = model.forward(image, label,)

            # loss = fluid.layers.square_error_cost(predict,label)
            loss = fluid.layers.cross_entropy(predict,label)
            avg_loss = fluid.layers.mean(loss)
            if batch_id%100 ==0:
                print("epoch:{},batch:{},loss is :{},acc:{}".format(epoch_id,batch_id,avg_loss.numpy(),avg_acc.numpy()))
                # data_writer.add_scalar("train/loss",avg_loss.numpy(),iter)
                # data_writer.add_scalar("train/accuracy",avg_acc.numpy(),iter)
                iter +=100
            avg_loss.backward()
            optimizer.minimize(avg_loss)
            model.clear_gradients()
        fluid.save_dygraph(model.state_dict(),'checkpoint/mnist_epoch{}'.format(epoch_id))
        fluid.save_dygraph(optimizer.state_dict(),'checkpoint/mnist_epoch{}'.format(epoch_id))




