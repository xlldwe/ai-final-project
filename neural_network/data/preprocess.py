import numpy as np
import tensorflow as tf
from tensorflow import keras
import matplotlib.pyplot as plt
import logging

logger = logging.getLogger(__name__)

CLASS_NAMES = [
    'T-shirt/top', 'Trouser', 'Pullover', 'Dress', 'Coat',
    'Sandal', 'Shirt', 'Sneaker', 'Bag', 'Ankle boot'
]


def load_fashion_mnist():
    """Load and preprocess Fashion MNIST dataset."""
    (x_train, y_train), (x_test, y_test) = keras.datasets.fashion_mnist.load_data()

    # Normalize to [0, 1]
    x_train = x_train.astype('float32') / 255.0
    x_test = x_test.astype('float32') / 255.0

    # Add channel dimension (28, 28) -> (28, 28, 1)
    x_train = np.expand_dims(x_train, -1)
    x_test = np.expand_dims(x_test, -1)

    # One-hot encode labels
    y_train_cat = keras.utils.to_categorical(y_train, 10)
    y_test_cat = keras.utils.to_categorical(y_test, 10)

    logger.info(f"Training samples: {len(x_train)}, Test samples: {len(x_test)}")
    return (x_train, y_train, y_train_cat), (x_test, y_test, y_test_cat)


def split_validation(x_train, y_train, y_train_cat, val_split=0.1):
    """Split training data into train and validation sets."""
    val_size = int(len(x_train) * val_split)
    x_val = x_train[:val_size]
    y_val = y_train_cat[:val_size]
    x_tr = x_train[val_size:]
    y_tr = y_train_cat[val_size:]
    return (x_tr, y_tr), (x_val, y_val)


def augment_dataset(x_train, y_train_cat):
    """Create augmented training dataset using Keras preprocessing."""
    dataset = tf.data.Dataset.from_tensor_slices((x_train, y_train_cat))

    def augment(image, label):
        image = tf.image.random_flip_left_right(image)
        image = tf.image.random_brightness(image, max_delta=0.1)
        image = tf.clip_by_value(image, 0.0, 1.0)
        return image, label

    dataset = dataset.map(augment, num_parallel_calls=tf.data.AUTOTUNE)
    dataset = dataset.shuffle(1000).batch(64).prefetch(tf.data.AUTOTUNE)
    return dataset


def visualize_samples(x_data, y_labels, n=25, save_path=None):
    """Visualize sample images from the dataset."""
    plt.figure(figsize=(10, 10))
    for i in range(n):
        plt.subplot(5, 5, i + 1)
        plt.xticks([])
        plt.yticks([])
        plt.grid(False)
        plt.imshow(x_data[i].reshape(28, 28), cmap='gray')
        plt.xlabel(CLASS_NAMES[y_labels[i]])
    plt.tight_layout()
    if save_path:
        plt.savefig(save_path)
    plt.show()


def preprocess_single_image(image_array):
    """Preprocess a single image for prediction."""
    if len(image_array.shape) == 2:
        image_array = np.expand_dims(image_array, -1)
    if image_array.max() > 1.0:
        image_array = image_array.astype('float32') / 255.0
    if len(image_array.shape) == 3:
        image_array = np.expand_dims(image_array, 0)
    return image_array


def preprocess_real_photo(image_bytes: bytes) -> np.ndarray:
    """
    Preprocess a real-world photo for Fashion MNIST model.
    Handles: background removal, centering, inversion to match dataset style.
    Returns shape (1, 28, 28, 1) normalized to [0, 1].
    """
    from PIL import Image
    import io

    img = Image.open(io.BytesIO(image_bytes)).convert('L')
    img = img.resize((224, 224), Image.LANCZOS)
    arr = np.array(img, dtype=np.float32)

    # Detect background color using image corners
    corners = [arr[0, 0], arr[0, -1], arr[-1, 0], arr[-1, -1]]
    bg_value = np.mean(corners)

    # Fashion MNIST: dark background, light clothing → invert real photos
    if bg_value > 100:
        arr = 255.0 - arr

    # Find bounding box of the clothing (non-background area)
    threshold = 40
    mask = arr > threshold
    rows = np.any(mask, axis=1)
    cols = np.any(mask, axis=0)

    if rows.any() and cols.any():
        rmin, rmax = np.where(rows)[0][[0, -1]]
        cmin, cmax = np.where(cols)[0][[0, -1]]
        pad = max(5, int((rmax - rmin) * 0.05))
        rmin = max(0, rmin - pad)
        rmax = min(arr.shape[0] - 1, rmax + pad)
        cmin = max(0, cmin - pad)
        cmax = min(arr.shape[1] - 1, cmax + pad)
        arr = arr[rmin:rmax + 1, cmin:cmax + 1]

    # Place on square canvas (centered)
    h, w = arr.shape
    size = max(h, w)
    square = np.zeros((size, size), dtype=np.float32)
    y_off = (size - h) // 2
    x_off = (size - w) // 2
    square[y_off:y_off + h, x_off:x_off + w] = arr

    # Resize to 28x28
    img_out = Image.fromarray(square.astype(np.uint8)).resize((28, 28), Image.LANCZOS)
    result = np.array(img_out, dtype='float32') / 255.0
    return result.reshape(1, 28, 28, 1)