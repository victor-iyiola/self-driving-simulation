"""Helper file for working with training dataset.

   @author 
     Victor I. Afolabi
     Artificial Intelligence & Software Engineer.
     Email: javafolabi@gmail.com
     GitHub: https://github.com/victor-iyiola
  
   @project
     File: data.py
     Created on 08 June, 2018 @ 8:27 PM.
  
   @license
     MIT License
     Copyright (c) 2018. Victor I. Afolabi. All rights reserved.
"""
import os

import numpy as np
import pandas as pd

import tensorflow as tf

# Path to where training data is collected (from the simulator).
data_dir = os.path.join(os.path.dirname(os.path.curdir), 'simulated_data')

# CSV File generated by the Simulator.
CSV_FILENAME = os.path.join(data_dir, 'driving_log.csv')
IMG_DIR = os.path.join(data_dir, 'IMG')

# CSV File header names.
FILE_NAMES = ['img_center', 'img_left', 'img_right',
              'center', 'left', 'right', 'steering_angle']

# Image dimensions.
img_size, channels = 32, 3

import cv2


# Use a custom OpenCV function to read the image, instead of the standard
# TensorFlow `tf.read_file()` operation.
def _read_py_function(filename, label):
    image_decoded = cv2.imread(filename.decode(), cv2.IMREAD_GRAYSCALE)
    return image_decoded, label


# Use standard TensorFlow operations to resize the image to a fixed shape.
def _resize_function(image_decoded, label):
    image_decoded.set_shape([None, None, None])
    image_resized = tf.image.resize_images(image_decoded, [28, 28])
    return image_resized, label


def _parser(filename: tf.string, label: tf.Tensor):
    """Reads an image from a file, decodes it into dense Tensor.

    Args:
        filename (tf.string): Path to the image file. [jpeg, png, gif & bmp]
        label (tf.Tensor): Associated label for this image.

    Returns:
        tuple: image_decoded, label
    """
    # Reads an image from a file, decodes it into a dense tensor,
    # resizes it to a fixed shape and cast into tf.float32
    image_string = tf.read_file(filename)
    image_decoded = tf.image.decode_image(image_string)
    image_decoded.set_shape([img_size, img_size, channels])
    image_cast = tf.cast(image_decoded, tf.float32)

    # Reshape label.
    label_reshape = tf.reshape(label, shape=(1,))

    return image_cast, label_reshape


def make_dataset(features: np.ndarray, labels: np.ndarray = None, **kwargs):
    # Extract keyword arguments.
    shuffle = kwargs.get('shuffle') or True
    buffer_size = kwargs.get('buffer_size') or 1000
    batch_size = kwargs.get('batch_size') or 128

    # Read CSV file into dataset object.
    if labels is not None:
        dataset = tf.data.Dataset.from_tensor_slices((features, labels))
        dataset = dataset.map(_parser)
    else:
        dataset = tf.data.Dataset.from_tensor_slices(features)
        dataset = dataset.map(lambda fname, label: tuple(tf.py_func(_read_py_function,
                                                                    [fname, label],
                                                                    [tf.uint8, label.dtype])))
        dataset = dataset.map(_resize_function)

    # Apply transformation steps...
    if shuffle:
        dataset = dataset.shuffle(buffer_size=buffer_size)
    dataset = dataset.batch(batch_size=batch_size)

    return dataset


def load_data(features: np.ndarray = None, **kwargs):
    # test_size = kwargs.get('test_size') or 0.1

    if features is None:
        # Read dataset from cvs file if there are no features.
        df = pd.read_csv(CSV_FILENAME, names=FILE_NAMES)

        # Extract features & labels.
        features = df[FILE_NAMES[0]].astype(str).values
        labels = df[FILE_NAMES[-1]].astype(np.float32).values

        # Create a dataset object.
        dataset = make_dataset(features, labels, **kwargs)
    else:
        dataset = make_dataset(features, labels=None, **kwargs)

    return dataset
