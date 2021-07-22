from collections import defaultdict, Counter

import numpy as np
from tqdm import tqdm

from hwr.constants import DATA


# get the ending alphabets given a word beam
def get_ending_alphas(text):
    end_alphas = ""
    for i in reversed(range(len(text))):
        if text[i].isalpha():
            end_alphas = text[i] + end_alphas
        else:
            break
    return end_alphas


# sm has dimension [sample, timestep, num_of_chars]
def trie_beam_search(rnn_out, bw, top_paths, trie=None, lm=None, lm_order=0, candidate_cap=5, gamma=0.5):
    return [__trie_beam_search(x, lm, trie, bw, top_paths, lm_order, candidate_cap, gamma) for x in tqdm(rnn_out)]


def __trie_beam_search(mat, lm, trie, bw, top_paths, lm_order, candidate_cap, gamma):
    # pb[t][beam]: P of {beam} at time {t} ending with blank '%'
    # pnb[t][beam]: P of {beam} at time {t} ending with any non blank chars
    # Ptxt[beam] : P of {beam} given a language model.
    pb, pnb, ptxt = defaultdict(Counter), defaultdict(Counter), {}
    timestep, chars_size = mat.shape
    # add a time step 0 for P(t-1) at t=1
    mat = np.vstack((np.zeros(chars_size), mat))
    pb[0][''] = 1
    pnb[0][''] = 0
    ptxt[''] = 1
    beams_prev = ['']

    for t in range(1, timestep + 1):
        for beam in beams_prev:
            # Get ending alphabet, try to form a word in the trie
            if trie:
                ending_alphas = get_ending_alphas(beam).lower()
                candidates = trie.get_char_candidates(ending_alphas)
                # Allow uppercase and non alphabets only when a word is form/ not being formed
                if trie.is_word(ending_alphas) or ending_alphas == "":
                    candidates += [c.upper() for c in candidates]
                    candidates += DATA.NON_ALPHAS
                candidates += "%"
            else:
                candidates = DATA.CHARS

            # Check only top n candidates for performance
            if len(candidates) > candidate_cap:
                candidates = sorted(candidates, key=lambda c: mat[t][DATA.CHARS.index(c)], reverse=True)[:candidate_cap]

            for char in candidates:
                # if candidate is blank
                if char == '%':
                    # Pb(beam,t) += mat(blank,t) * Ptotal(beam,t-1)
                    pb[t][beam] += mat[t][-1] * (pb[t - 1][beam] + pnb[t - 1][beam])

                # if candidate is non-blank
                else:
                    new_beam = beam + char
                    letter_idx = DATA.CHARS.index(char)

                    # Apply character level language model and calculate Ptxt(beam)
                    if lm:
                        if new_beam not in ptxt.keys():
                            # Ptxt(beam+c) = P(c|last n char in beam)
                            prefix = beam[-(lm_order - 1):]
                            ptxt[new_beam] = lm.score(char.lower(), [p for p in prefix.lower()])
                    else:
                        ptxt[new_beam] = 1

                    # if new candidate and last char in the beam is same
                    if len(beam) > 0 and char == beam[-1]:
                        # Pnb(beam+c,t) += mat(c,t) * Pb(beam,t-1)
                        pnb[t][new_beam] += mat[t][letter_idx] * pb[t - 1][beam]
                        # Pnb(beam,t) = mat(c,t) * Pnb(beam,t-1)
                        pnb[t][beam] += mat[t][letter_idx] * pnb[t - 1][beam]
                    else:
                        # Pnb(beam+c,t) = mat(c,t) * Ptotal(beam,t-1)
                        pnb[t][new_beam] += mat[t][letter_idx] * (pb[t - 1][beam] + pnb[t - 1][beam])
        Ptotal_t = pb[t] + pnb[t]
        # sort by Ptotal * weighted Ptxt
        sort = lambda k: Ptotal_t[k] * (ptxt[k] ** gamma)
        # Top (bw) beams for next iteration
        beams_prev = sorted(Ptotal_t, key=sort, reverse=True)[:bw]

    return beams_prev[:top_paths]



















