import sys
from utils import *

def load_model():
    src_vocab = load_vocab(sys.argv[2], "src")
    tgt_vocab = load_vocab(sys.argv[3], "tgt")
    tgt_vocab = [x for x, _ in sorted(tgt_vocab.items(), key = lambda x: x[1])]
    enc = encoder(len(src_vocab))
    dec = decoder(len(tgt_vocab))
    enc.eval()
    dec.eval()
    print(enc)
    print(dec)
    load_checkpoint(sys.argv[1], enc, dec)
    return enc, dec, src_vocab, tgt_vocab

def run_model(enc, dec, tgt_vocab, data):
    z = len(data)
    eos = [0 for _ in range(z)] # number of EOS tokens in the batch
    while len(data) < BATCH_SIZE:
        data.append([-1, [], [EOS_IDX], [], 0])
    for x in data:
        print(x)
    data.sort(key = lambda x: len(x[2]), reverse = True)
    batch_len = len(data[0][2])
    batch = LongTensor([x[2] + [PAD_IDX] * (batch_len - len(x[2])) for x in data])
    mask = maskset(batch)
    enc_out = enc(batch, mask)
    dec_in = LongTensor([SOS_IDX] * BATCH_SIZE).unsqueeze(1)
    dec.hidden = enc.hidden
    if dec.feed_input:
        dec.attn.hidden = zeros(BATCH_SIZE, 1, HIDDEN_SIZE)
    t = 0
    if VERBOSE:
        heatmap = [[[""] + x[1] + [EOS]] for x in data[:z]] # attention heat map
    while sum(eos) < z and t < MAX_LEN:
        dec_out = dec(dec_in, enc_out, t, mask)
        y = [(b, a) for x in zip(*dec_out.topk(BEAM_SIZE)) for a, b in zip(*x)]
        for a, b in y:
            print(tgt_vocab[a], b)
        dec_in = dec_out.topk(1)[1]
        y = dec_in.view(-1).tolist()[:z]
        for i in range(z):
            if eos[i]:
                continue
            if y[i] == EOS_IDX:
                eos[i] = 1
                continue
            k = tgt_vocab[y[i]]
            data[i][3].append(k)
            if VERBOSE:
                heatmap[i].append([k] + dec.attn.Va[i][0].tolist())
        t += 1
    if VERBOSE:
        for m in heatmap:
            print(mat2csv(m, rh = True))
    return [(x[1], x[3]) for x in sorted(data[:z])] 
def predict():
    idx = 0
    data = []
    result = []
    enc, dec, src_vocab, tgt_vocab = load_model()
    fo = open(sys.argv[4])
    for line in fo:
        line = tokenize(line, UNIT)
        x = [src_vocab[i] if i in src_vocab else UNK_IDX for i in line] + [EOS_IDX]
        data.extend([[idx, line, x, [], 0] for _ in range(BEAM_SIZE)])
        if len(data) == BATCH_SIZE:
            result.extend(run_model(enc, dec, tgt_vocab, data))
            data = []
        idx += 1
    fo.close()
    if len(data):
        result.extend(run_model(enc, dec, tgt_vocab, data))
    for x in result:
        print(x)

if __name__ == "__main__":
    if len(sys.argv) != 5:
        sys.exit("Usage: %s model vocab.src vocab.tgt test_data" % sys.argv[0])
    print("cuda: %s" % CUDA)
    print("batch size: %d" % BATCH_SIZE)
    with torch.no_grad():
        predict()
