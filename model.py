"""Based on Nvidia's Paper on End-to-end learning for self driving car.

   @author 
     Victor I. Afolabi
     Artificial Intelligence & Software Engineer.
     Email: javafolabi@gmail.com
     GitHub: https://github.com/victor-iyiola/
  
   @project
     File: model.py
     Created on 18 May, 2018 @ 5:26 PM.
  
   @license
     MIT License
     Copyright (c) 2018. Victor I. Afolabi. All rights reserved.
"""
import os.path
import argparse
import logging

import tensorflow as tf
import data

# Logging configurations.
FORMAT = '[%(name)s:%(lineno)d] %(levelname)s: %(message)s'
logging.basicConfig(format=FORMAT, level=logging.DEBUG)
tf.logging.set_verbosity(tf.logging.WARN)


# noinspection PyAbstractClass
class Model(tf.keras.Model):
    def __init__(self, args):
        super(Model, self).__init__()

        # Command line arguments.
        self.args = args

        # Convolutional Layers / Feature Extraction
        self.conv1 = tf.keras.layers.Conv2D(filters=24, kernel_size=5,
                                            padding='same', activation='elu')
        self.conv2 = tf.keras.layers.Conv2D(filters=36, kernel_size=5,
                                            padding='same', activation='elu')
        self.conv3 = tf.keras.layers.Conv2D(filters=48, kernel_size=5,
                                            padding='same', activation='elu')
        self.conv4 = tf.keras.layers.Conv2D(filters=64, kernel_size=3,
                                            padding='same', activation='elu')
        self.conv5 = tf.keras.layers.Conv2D(filters=64, kernel_size=3,
                                            padding='same', activation='elu')

        # Flatten & apply dropout.
        self.flatten = tf.keras.layers.Flatten()
        self.dropout = tf.keras.layers.Dropout(rate=self.args.dropout)

        # Fully connected / Dense layers.
        self.dense1 = tf.keras.layers.Dense(units=100, activation='elu')
        self.dense2 = tf.keras.layers.Dense(units=50, activation='elu')
        self.dense3 = tf.keras.layers.Dense(units=10, activation='elu')

        # Prediction / Output layer.
        self.pred_layer = tf.keras.layers.Dense(units=1)

    def __call__(self, inputs, *args, **kwargs):
        return super().__call__(inputs, *args, **kwargs)

    def call(self, inputs, **kwargs):
        with tf.name_scope('model'):
            # Network layers.
            with tf.name_scope('layers'):
                # Input layer.
                with tf.name_scope('input'):
                    net = tf.reshape(inputs,
                                     shape=(-1, self.args.img_size,
                                            self.args.img_size, self.args.img_depth),
                                     name='reshape')

                # Convolutional layers.
                with tf.name_scope('feature_extraction'):
                    net = self.conv2(self.conv1(net))
                    net = self.conv4(self.conv3(net))
                    net = self.conv5(net)

                # Fully connected / Dense layers.
                with tf.name_scope('fully_connected'):
                    net = self.flatten(net)
                    net = self.dense1(self.dropout(net))
                    net = self.dense3(self.dense2(net))

                # Prediction / Output layer.
                with tf.name_scope('prediction'):
                    net = self.pred_layer(net)

        return net


def loss_fn(predictions, labels):
    with tf.name_scope('loss'):
        # loss = tf.keras.losses.categorical_crossentropy(y_true=labels, y_pred=predictions)
        # loss = tf.reduce_mean(loss)
        loss = tf.losses.mean_squared_error(labels=labels, predictions=predictions,
                                            reduction=tf.losses.Reduction.MEAN)
    return loss


def train(args):
    dataset = data.load_data(**vars(args))
    iterator = dataset.make_initializable_iterator()
    features, labels = iterator.get_next()

    model = Model(args)
    predictions = model(features)

    loss = loss_fn(predictions, labels)
    tf.summary.scalar('loss', loss)

    # Minimize loss (train the model).
    optimizer = tf.train.RMSPropOptimizer(learning_rate=args.learning_rate)
    global_step = tf.train.get_or_create_global_step()
    train_op = optimizer.minimize(loss=loss, global_step=global_step,
                                  name='train_op')
    merged = tf.summary.merge_all()

    with tf.Session() as sess:
        # Initialize global variables.
        init = tf.global_variables_initializer()

        save_dir = os.path.dirname(args.save_path)

        saver = tf.train.Saver()
        writer = tf.summary.FileWriter(logdir=args.log_dir, graph=sess.graph)

        # DEBUGGING:
        # sess.run([init, iterator.initializer])
        # _p, _l, _lo = sess.run([predictions, labels, loss])
        # print('Predictions', _p)
        # print('Labels', _l)
        # print('Loss', _lo)

        if tf.gfile.Exists(save_dir):
            try:
                ckpt_path = tf.train.latest_checkpoint(save_dir)
                saver.restore(sess=sess, save_path=ckpt_path)
                logging.info('Restored checkpoint from {}'.format(ckpt_path))
            except Exception:
                logging.warning('Could not load checkpoint. Initializing global variables.')
                sess.run(init)
        else:
            # Create checkpoint directory.
            tf.gfile.MakeDirs(save_dir)

            # Initialize global variables.
            logging.info('No checkpoint. Initializing global variables.')
            sess.run(init)

        for epoch in range(args.epochs):
            try:
                # Run dataset initializer.
                sess.run(iterator.initializer)
                while True:
                    try:
                        # Run train operation.
                        _, _step, _loss = sess.run([train_op, global_step, loss])

                        print('\rEpoch: {:,} Step: {:,} Loss: {:.2f}'
                              .format(epoch, _step, _loss), end='')

                        if _step % args.log_every == 0:
                            summary = sess.run(merged)
                            writer.add_summary(summary, global_step=_step)

                        if _step % args.save_every == 0:
                            print('\n{0}\nSaving model...'.format('-' * 55))
                            saver.save(sess=sess, save_path=args.save_path,
                                       global_step=global_step)
                            print('{0}\n'.format('-' * 55))

                    except tf.errors.OutOfRangeError:
                        break
            except KeyboardInterrupt:
                print('\n{0}\nTraining interrupted by user!'.format('-' * 55))
                print('Saving model to {}'.format(args.save_path))

                saver.save(sess=sess, save_path=args.save_path,
                           global_step=global_step)

                print('{0}\n'.format('-' * 55))

                # !- End training.
                break


if __name__ == '__main__':
    parser = argparse.ArgumentParser()

    # Data dimension.
    parser.add_argument('-channels', dest='img_depth', type=int, default=3,
                        help='Image channels. One of (None, 0, 1, 2, 3 or 4)')
    parser.add_argument('-img_size', dest='img_size', type=int, default=32,
                        help='Size of input image to the network.')

    parser.add_argument('-b', dest='batch_size', type=int, default=64,
                        help='Mini-batch size.')
    parser.add_argument('-dr', dest='dropout', type=float, default=0.5,
                        help='Dropout rate. Probability of randomly turning off neurons.')
    parser.add_argument('-lr', dest='learning_rate', type=float, default=1e-2,
                        help='Optimizer\'s learning rate.')

    # Training arguments.
    parser.add_argument('--log_every', dest='log_every', type=int, default=20,
                        help='Interval to log summaries to Tensorboard.')
    parser.add_argument('--save_every', dest='save_every', type=int, default=10,
                        help='Intervals to save model checkpoints.')
    parser.add_argument('-e', dest='epochs', type=int, default=1000,
                        help='Number of training epochs.')

    # Data & checkpoint arguments.
    # parser.add_argument('-d', dest='data_dir', type=str, default='./simulations/',
    #                     help='Directory where simulated data is stored.')
    parser.add_argument('-log', dest='log_dir', type=str, default='./saved/logs/',
                        help='Path to write Tensorboard event logs.')
    parser.add_argument('-d', dest='data_dir', type=str, default='./simulated_data/',
                        help='Directory where simulated data is stored.')
    parser.add_argument('-s', dest='save_path', type=str, default='./saved/models/nvidia.ckpt',
                        help='Checkpoint saved path.')

    # Parsed arguments.
    args = parser.parse_args()

    print('{0}\n{1:^55}\n{0}'.format('-' * 55, 'Command Line Arguments'))
    for k, v in vars(args).items():
        print('{:<20} = {:>30}'.format(k, v))
    print('{}\n'.format('-' * 55))

    # Update data directory.
    data.data_dir = args.data_dir

    train(args=args)
