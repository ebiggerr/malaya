from malaya.function import check_file, load_graph, generate_session
from malaya.text.bpe import (
    sentencepiece_tokenizer_bert,
    sentencepiece_tokenizer_xlnet,
)
from malaya.text.trees import tree_from_str
from malaya.path import PATH_CONSTITUENCY, S3_PATH_CONSTITUENCY
from malaya.model.tf import Constituency
import json
from herpetologist import check_type

_transformer_availability = {
    'bert': {
        'Size (MB)': 470.0,
        'Quantized Size (MB)': 118.0,
        'Recall': 78.96,
        'Precision': 81.78,
        'FScore': 80.35,
        'CompleteMatch': 10.37,
        'TaggingAccuracy': 91.59,
    },
    'tiny-bert': {
        'Size (MB)': 125.0,
        'Quantized Size (MB)': 31.8,
        'Recall': 74.89,
        'Precision': 78.79,
        'FScore': 76.79,
        'CompleteMatch': 9.01,
        'TaggingAccuracy': 91.17,
    },
    'albert': {
        'Size (MB)': 180.0,
        'Quantized Size (MB)': 45.7,
        'Recall': 77.57,
        'Precision': 80.50,
        'FScore': 79.01,
        'CompleteMatch': 5.77,
        'TaggingAccuracy': 90.30,
    },
    'tiny-albert': {
        'Size (MB)': 56.7,
        'Quantized Size (MB)': 14.5,
        'Recall': 67.21,
        'Precision': 74.89,
        'FScore': 70.84,
        'CompleteMatch': 2.11,
        'TaggingAccuracy': 87.75,
    },
    'xlnet': {
        'Size (MB)': 498.0,
        'Quantized Size (MB)': 126.0,
        'Recall': 81.52,
        'Precision': 85.18,
        'FScore': 83.31,
        'CompleteMatch': 11.71,
        'TaggingAccuracy': 91.71,
    },
}

_vectorizer_mapping = {
    'bert': 'import/bert/encoder/layer_11/output/LayerNorm/batchnorm/add_1:0',
    'tiny-bert': 'import/bert/encoder/layer_11/output/LayerNorm/batchnorm/add_1:0',
    'albert': 'import/bert/encoder/transformer/group_0_11/layer_11/inner_group_0/LayerNorm_1/batchnorm/add_1:0',
    'tiny-albert': 'import/bert/encoder/transformer/group_0_3/layer_3/inner_group_0/LayerNorm_1/batchnorm/add_1:0',
    'xlnet': 'import/model/transformer/layer_11/ff/LayerNorm/batchnorm/add_1:0',
}


def available_transformer():
    """
    List available transformer models.
    """
    from malaya.function import describe_availability

    return describe_availability(
        _transformer_availability, text = 'tested on 20% test set.'
    )


@check_type
def transformer(model: str = 'xlnet', quantized: bool = False, **kwargs):
    """
    Load Transformer Constituency Parsing model, transfer learning Transformer + self attentive parsing.

    Parameters
    ----------
    model : str, optional (default='bert')
        Model architecture supported. Allowed values:

        * ``'bert'`` - Google BERT BASE parameters.
        * ``'tiny-bert'`` - Google BERT TINY parameters.
        * ``'albert'`` - Google ALBERT BASE parameters.
        * ``'tiny-albert'`` - Google ALBERT TINY parameters.
        * ``'xlnet'`` - Google XLNET BASE parameters.
    
    quantized : bool, optional (default=False)
        if True, will load 8-bit quantized model. 
        Quantized model not necessary faster, totally depends on the machine.

    Returns
    -------
    result : malaya.model.tf.Constituency class
    """

    model = model.lower()
    if model not in _transformer_availability:
        raise ValueError(
            'model not supported, please check supported models from `malaya.constituency.available_transformer()`.'
        )

    check_file(
        PATH_CONSTITUENCY[model],
        S3_PATH_CONSTITUENCY[model],
        quantized = quantized,
        **kwargs,
    )
    if quantized:
        model_path = 'quantized'
    else:
        model_path = 'model'
    g = load_graph(PATH_CONSTITUENCY[model][model_path], **kwargs)

    with open(PATH_CONSTITUENCY[model]['dictionary']) as fopen:
        dictionary = json.load(fopen)

    if model in ['bert', 'tiny-bert', 'albert', 'tiny-albert']:

        tokenizer = sentencepiece_tokenizer_bert(
            PATH_CONSTITUENCY[model]['tokenizer'],
            PATH_CONSTITUENCY[model]['vocab'],
        )
        mode = 'bert'

    if model in ['xlnet']:
        tokenizer = sentencepiece_tokenizer_xlnet(
            PATH_CONSTITUENCY[model]['tokenizer']
        )
        mode = 'xlnet'

    return Constituency(
        input_ids = g.get_tensor_by_name('import/input_ids:0'),
        word_end_mask = g.get_tensor_by_name('import/word_end_mask:0'),
        charts = g.get_tensor_by_name('import/charts:0'),
        tags = g.get_tensor_by_name('import/tags:0'),
        vectorizer = g.get_tensor_by_name(_vectorizer_mapping[model]),
        sess = generate_session(graph = g, **kwargs),
        tokenizer = tokenizer,
        dictionary = dictionary,
        mode = mode,
    )
