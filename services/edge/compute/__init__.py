"""Edge compute: ONNX Runtime inference engine."""
from services.edge.compute.inference import EdgeInferenceEngine, ModelInfo  # noqa: F401

__all__ = ["EdgeInferenceEngine", "ModelInfo"]
