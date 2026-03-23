import os
import sys
import numpy as np
import time
import logging

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from neural_network.model import load_model
from neural_network.data.preprocess import CLASS_NAMES, preprocess_single_image

logger = logging.getLogger(__name__)

_model = None


def get_model(model_path='neural_network/models/best_model.keras'):
    global _model
    if _model is None:
        _model = load_model(model_path)
    return _model


def predict_image(image_array, model_path='neural_network/models/best_model.keras'):
    """
    Predict clothing class for a single image.

    Args:
        image_array: numpy array of shape (28, 28), (28, 28, 1), or (1, 28, 28, 1)

    Returns:
        dict with 'class', 'confidence', 'all_probabilities', 'inference_time_ms'
    """
    model = get_model(model_path)
    if model is None:
        return {'error': 'Model not loaded. Run train.py first.'}

    processed = preprocess_single_image(image_array)

    start = time.time()
    predictions = model.predict(processed, verbose=0)
    elapsed_ms = (time.time() - start) * 1000

    pred_class_idx = int(np.argmax(predictions[0]))
    confidence = float(predictions[0][pred_class_idx])

    all_probs = {CLASS_NAMES[i]: float(predictions[0][i]) for i in range(10)}

    return {
        'class': CLASS_NAMES[pred_class_idx],
        'class_index': pred_class_idx,
        'confidence': confidence,
        'confidence_pct': f"{confidence * 100:.2f}%",
        'all_probabilities': all_probs,
        'inference_time_ms': round(elapsed_ms, 2)
    }


def predict_batch(images_array, model_path='neural_network/models/best_model.keras'):
    """Predict classes for a batch of images."""
    model = get_model(model_path)
    if model is None:
        return [{'error': 'Model not loaded'}]

    processed = np.array([preprocess_single_image(img)[0] for img in images_array])

    start = time.time()
    predictions = model.predict(processed, verbose=0)
    elapsed_ms = (time.time() - start) * 1000

    results = []
    for i, pred in enumerate(predictions):
        idx = int(np.argmax(pred))
        results.append({
            'class': CLASS_NAMES[idx],
            'class_index': idx,
            'confidence': float(pred[idx]),
            'confidence_pct': f"{float(pred[idx]) * 100:.2f}%",
        })

    logger.info(f"Batch prediction: {len(images_array)} images in {elapsed_ms:.2f}ms")
    return results


def demo_prediction():
    """Run a demo prediction on random Fashion MNIST test samples."""
    from tensorflow.keras.datasets import fashion_mnist
    import matplotlib.pyplot as plt

    (_, _), (x_test, y_test) = fashion_mnist.load_data()
    x_test = x_test.astype('float32') / 255.0

    indices = np.random.choice(len(x_test), 5, replace=False)

    print("Demo Predictions:")
    print("-" * 60)
    for idx in indices:
        result = predict_image(x_test[idx])
        true_label = CLASS_NAMES[y_test[idx]]
        correct = "V" if result['class'] == true_label else "X"
        print(f"{correct} True: {true_label:15} | Predicted: {result['class']:15} | Confidence: {result['confidence_pct']} | Time: {result['inference_time_ms']}ms")


if __name__ == '__main__':
    demo_prediction()