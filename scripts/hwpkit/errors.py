class HwpxError(Exception):
    """Base error with a stable machine-readable code."""

    code = "HWPX_ERROR"

    def as_dict(self) -> dict[str, str]:
        return {"code": self.code, "message": str(self)}


class SpecError(HwpxError):
    code = "INVALID_DOCUMENT_SPEC"


class ConformanceError(HwpxError):
    code = "FEATURE_NOT_CONFORMANCE_VERIFIED"


class ValidationError(HwpxError):
    code = "HWPX_VALIDATION_FAILED"

