from model_benchmark import benchmark_model


def test_benchmark_records_model_latency_and_response_size():
    result = benchmark_model(
        "qwen3:0.6b",
        "Say hi.",
        chat=lambda **_: {"message": {"content": "hello"}},
    )

    assert result["model"] == "qwen3:0.6b"
    assert result["response_characters"] == 5
    assert result["latency_seconds"] >= 0
