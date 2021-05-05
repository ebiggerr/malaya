import os

os.environ['CUDA_VISIBLE_DEVICES'] = '3'

from tensor2tensor.data_generators import problem
from tensor2tensor.data_generators import text_problems
from tensor2tensor.data_generators import translate
from tensor2tensor.utils import registry
from tensor2tensor import problems
import tensorflow as tf
import os
import logging

logger = logging.getLogger()
tf.logging.set_verbosity(tf.logging.DEBUG)

import sentencepiece as spm

vocab = 'sp10m.cased.t5.model'
sp = spm.SentencePieceProcessor()
sp.Load(vocab)


class Encoder:
    def __init__(self, sp):
        self.sp = sp
        self.vocab_size = sp.GetPieceSize() + 100

    def encode(self, s):
        return self.sp.EncodeAsIds(s)

    def decode(self, ids, strip_extraneous = False):
        return self.sp.DecodeIds(list(ids))


encoder = Encoder(sp)

from tqdm import tqdm
from glob import glob


@registry.register_problem
class Seq2Seq(text_problems.Text2TextProblem):
    @property
    def approx_vocab_size(self):
        return 32100

    @property
    def is_generate_per_split(self):
        return False

    @property
    def dataset_splits(self):
        return [{'split': problem.DatasetSplit.TRAIN, 'shards': 500}]

    def feature_encoders(self, data_dir):
        encoder = Encoder(sp)
        return {'inputs': encoder, 'targets': encoder}


# os.system('rm -rf t2t-summarization-1024/train-base')
os.system('mkdir t2t-summarization-1024/train-base')
DATA_DIR = os.path.expanduser('t2t-summarization-1024/data')
TMP_DIR = os.path.expanduser('t2t-summarization-1024/tmp')
TRAIN_DIR = os.path.expanduser('t2t-summarization-1024/train-base')

PROBLEM = 'seq2_seq'
t2t_problem = problems.problem(PROBLEM)

train_steps = 1000000
eval_steps = 10
batch_size = 1024 * 5
save_checkpoints_steps = 25000
ALPHA = 0.001
schedule = 'continuous_train_and_eval'
MODEL = 'transformer'
HPARAMS = 'transformer_base'

from tensor2tensor.utils.trainer_lib import create_run_config, create_experiment
from tensor2tensor.utils.trainer_lib import create_hparams
from tensor2tensor.utils import registry
from tensor2tensor import models
from tensor2tensor import problems

hparams = create_hparams(HPARAMS)
hparams.batch_size = batch_size
hparams.learning_rate = ALPHA

hparams.filter_size = 3072
hparams.hidden_size = 768
hparams.num_heads = 12
hparams.num_hidden_layers = 8
hparams.vocab_divisor = 128
hparams.label_smoothing = 0.0
hparams.shared_embedding_and_softmax_weights = False
hparams.dropout = 0.1
hparams.max_length = 1024
hparams.multiproblem_mixing_schedule = 'pretrain'

hparams.optimizer = 'Adafactor'
hparams.learning_rate_warmup_steps = 10000
hparams.learning_rate_schedule = 'rsqrt_decay'
hparams.warm_start_from_second = 'base/model.ckpt-500000'

print(hparams)

RUN_CONFIG = create_run_config(
    model_dir = TRAIN_DIR,
    model_name = MODEL,
    save_checkpoints_steps = save_checkpoints_steps,
    num_gpus = 1,
    gpu_mem_fraction = 0.97,
    schedule = 'train',
)

tensorflow_exp_fn = create_experiment(
    run_config = RUN_CONFIG,
    hparams = hparams,
    model_name = MODEL,
    problem_name = PROBLEM,
    data_dir = DATA_DIR,
    train_steps = train_steps,
    eval_steps = eval_steps,
    schedule = 'train',
    # use_xla=True # For acceleration
)

tensorflow_exp_fn.train()
