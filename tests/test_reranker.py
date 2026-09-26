from reranker import OnnxCrossEncoderReranker


class FakeTokenizer:
    def __call__(self, questions, passages, **kwargs):
        assert questions == ["what is gradient descent?"] * 3
        return {"input_ids": [[1], [2], [3]], "attention_mask": [[1], [1], [1]]}


class Input:
    name = "input_ids"


class FakeSession:
    def get_inputs(self):
        return [Input()]

    def run(self, output_names, inputs):
        assert set(inputs) == {"input_ids"}
        return [[[0.2], [0.9], [0.4]]]


class Candidate:
    def __init__(self, text):
        self.payload = {"text": text}


def test_onnx_reranker_orders_candidates_by_cross_encoder_score():
    reranker = OnnxCrossEncoderReranker("unused", tokenizer=FakeTokenizer(), session=FakeSession())
    candidates = [Candidate("first"), Candidate("second"), Candidate("third")]

    ranked = reranker.rerank("what is gradient descent?", candidates, top_k=2)

    assert [item.payload["text"] for item in ranked] == ["second", "third"]
