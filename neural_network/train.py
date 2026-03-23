import os
import sys
import logging
import numpy as np
import matplotlib.pyplot as plt

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neural_network.model import build_cnn_model, compile_model, get_callbacks
from neural_network.data.preprocess import load_fashion_mnist, split_validation, augment_dataset

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

EPOCHS = 30
BATCH_SIZE = 64
LEARNING_RATE = 0.001
MODEL_PATH = 'neural_network/models/best_model.keras'
RESULTS_DIR = 'neural_network/results'


def plot_history(history, save_dir=RESULTS_DIR):
    os.makedirs(save_dir, exist_ok=True)

    fig, (ax1, ax2) = plt.subplots(1, 2, figsize=(12, 4))

    ax1.plot(history.history['accuracy'], label='Train Accuracy')
    ax1.plot(history.history['val_accuracy'], label='Val Accuracy')
    ax1.set_title('Model Accuracy')
    ax1.set_xlabel('Epoch')
    ax1.set_ylabel('Accuracy')
    ax1.legend()
    ax1.grid(True)

    ax2.plot(history.history['loss'], label='Train Loss')
    ax2.plot(history.history['val_loss'], label='Val Loss')
    ax2.set_title('Model Loss')
    ax2.set_xlabel('Epoch')
    ax2.set_ylabel('Loss')
    ax2.legend()
    ax2.grid(True)

    plt.tight_layout()
    plt.savefig(os.path.join(save_dir, 'training_history.png'), dpi=150)
    plt.show()
    logger.info(f"Training history plot saved to {save_dir}")


def train():
    logger.info("Loading Fashion MNIST dataset...")
    (x_train, y_train, y_train_cat), (x_test, y_test, y_test_cat) = load_fashion_mnist()

    (x_tr, y_tr), (x_val, y_val) = split_validation(x_train, y_train, y_train_cat)
    logger.info(f"Train: {len(x_tr)}, Val: {len(x_val)}, Test: {len(x_test)}")

    train_dataset = augment_dataset(x_tr, y_tr)

    logger.info("Building CNN model...")
    model = build_cnn_model()
    model = compile_model(model, learning_rate=LEARNING_RATE)
    model.summary()

    callbacks = get_callbacks(MODEL_PATH)

    logger.info("Starting training...")
    history = model.fit(
        train_dataset,
        epochs=EPOCHS,
        validation_data=(x_val, y_val),
        callbacks=callbacks,
        verbose=1
    )

    logger.info("Evaluating on test set...")
    test_loss, test_acc = model.evaluate(x_test, y_test_cat, verbose=0)
    logger.info(f"Test Loss: {test_loss:.4f}, Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")

    plot_history(history)

    return model, history, test_acc


if __name__ == '__main__':
    model, history, test_acc = train()
    print(f"\n{'='*50}")
    print(f"Training complete!")
    print(f"Final test accuracy: {test_acc*100:.2f}%")
    print(f"Model saved to: {MODEL_PATH}")