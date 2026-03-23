import os
import sys
import numpy as np
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.metrics import classification_report, confusion_matrix

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neural_network.model import load_model
from neural_network.data.preprocess import load_fashion_mnist, CLASS_NAMES

RESULTS_DIR = 'neural_network/results'


def evaluate_model(model_path='neural_network/models/best_model.keras'):
    os.makedirs(RESULTS_DIR, exist_ok=True)

    print("Loading dataset...")
    (_, _, _), (x_test, y_test, y_test_cat) = load_fashion_mnist()

    print("Loading model...")
    model = load_model(model_path)
    if model is None:
        print("Model not found. Please run train.py first.")
        return

    print("Running predictions...")
    y_pred_proba = model.predict(x_test, verbose=0)
    y_pred = np.argmax(y_pred_proba, axis=1)

    # Overall metrics
    test_loss, test_acc = model.evaluate(x_test, y_test_cat, verbose=0)
    print(f"\nTest Loss: {test_loss:.4f}")
    print(f"Test Accuracy: {test_acc:.4f} ({test_acc*100:.2f}%)")

    # Classification report
    print("\nClassification Report:")
    print(classification_report(y_test, y_pred, target_names=CLASS_NAMES))

    # Confusion matrix
    cm = confusion_matrix(y_test, y_pred)
    plt.figure(figsize=(12, 10))
    sns.heatmap(cm, annot=True, fmt='d', cmap='Blues',
                xticklabels=CLASS_NAMES, yticklabels=CLASS_NAMES)
    plt.title('Confusion Matrix - FashionCNN')
    plt.ylabel('True Label')
    plt.xlabel('Predicted Label')
    plt.xticks(rotation=45, ha='right')
    plt.tight_layout()
    plt.savefig(os.path.join(RESULTS_DIR, 'confusion_matrix.png'), dpi=150)
    plt.show()

    # Show misclassified examples
    misclassified = np.where(y_pred != y_test)[0]
    print(f"\nMisclassified samples: {len(misclassified)} / {len(y_test)}")

    # Plot some misclassified
    if len(misclassified) > 0:
        plt.figure(figsize=(12, 6))
        for i, idx in enumerate(misclassified[:10]):
            plt.subplot(2, 5, i + 1)
            plt.imshow(x_test[idx].reshape(28, 28), cmap='gray')
            plt.title(f"True: {CLASS_NAMES[y_test[idx]]}\nPred: {CLASS_NAMES[y_pred[idx]]}", fontsize=7)
            plt.axis('off')
        plt.suptitle('Misclassified Samples')
        plt.tight_layout()
        plt.savefig(os.path.join(RESULTS_DIR, 'misclassified.png'), dpi=150)
        plt.show()

    return test_acc


if __name__ == '__main__':
    evaluate_model()