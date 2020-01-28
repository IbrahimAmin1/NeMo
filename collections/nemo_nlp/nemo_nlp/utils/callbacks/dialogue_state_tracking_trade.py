# Copyright (c) 2019 NVIDIA Corporation
__all__ = ['eval_iter_callback', 'eval_epochs_done_callback']

import numpy as np
import torch

from nemo.utils.exp_logging import get_logger

logger = get_logger('')


def eval_iter_callback(tensors,
                       global_vars,
                       data_desc):

    if 'loss' not in global_vars:
        global_vars['loss'] = []
    if 'comp_res' not in global_vars:
        global_vars['comp_res'] = []
    if 'gating_labels' not in global_vars:
        global_vars['gating_labels'] = []
    if 'gating_preds' not in global_vars:
        global_vars['gating_preds'] = []

    for kv, v in tensors.items():
        if kv.startswith('loss'):
            loss_numpy = v[0].cpu().numpy()
            global_vars['loss'].append(loss_numpy)
        if kv.startswith('point_outputs'):
            point_outputs = v[0].cpu().numpy()
            # point_outputs = v[0]  # .cpu().numpy()
        if kv.startswith('gate_outputs'):
            gate_outputs = v[0].cpu().numpy()
            # gate_outputs = v[0]  # .cpu().numpy()
        if kv.startswith('gating_labels'):
            gating_labels = v[0].cpu().numpy()
            global_vars['gating_labels'].extend(gating_labels)
        if kv.startswith('tgt_ids'):
            tgt_ids = v[0].cpu().numpy()
            # tgt_ids = v[0] #.cpu().numpy()

    # point_outputs_max = torch.argmax(point_outputs, dim=-1)
    # mask_paddings = (tgt_ids == eval_data_layer.pad_id)
    # comp_res = ((point_outputs_max == tgt_ids) | mask_paddings)
    # comp_res = torch.all(comp_res, axis=-1, keepdims=False)

    point_outputs_max = np.argmax(point_outputs, axis=-1)
    mask_paddings = (tgt_ids == data_desc.pad_id)
    comp_res = np.logical_or(point_outputs_max == tgt_ids, mask_paddings)
    comp_res = np.all(comp_res, axis=-1, keepdims=False)

    #global_vars['comp_res'].extend(comp_res.cpu().numpy())
    global_vars['comp_res'].extend(comp_res)
    global_vars['gating_preds'].extend(np.argmax(gate_outputs, axis=-1))
    #global_vars['gating_preds'].extend(torch.argmax(gate_outputs, axis=-1).cpu().numpy())


def eval_epochs_done_callback(global_vars, data_desc):
    joint_acc, turn_acc = \
        evaluate_metrics(global_vars['comp_res'],
                         global_vars['gating_labels'],
                         global_vars['gating_preds'],
                         data_desc.gating_dict["ptr"])

    gating_comp_flatten = (np.asarray(global_vars['gating_labels']) == np.asarray(global_vars['gating_preds'])).ravel()
    gating_acc = np.sum(gating_comp_flatten) / len(gating_comp_flatten)

    evaluation_metrics = {"Joint_Goal_Acc": joint_acc,
                          "Turn_Acc": turn_acc,
                          "Gate_Acc": gating_acc}
    print(evaluation_metrics)

    return evaluation_metrics


def evaluate_metrics(comp_res, gating_labels, gating_preds, ptr_code):
    # TODO: Calculate precision, recall, and F1
    total_slots = 0
    correct_slots = 0
    total_turns = 0
    correct_turns = 0
    for result_idx, result in enumerate(comp_res):
        turn_wrong = False
        total_turns += 1
        for slot_idx, slot_eq in enumerate(result):
            total_slots += 1
            if gating_labels[result_idx][slot_idx] == ptr_code:
                if slot_eq:
                    correct_slots += 1
                else:
                    turn_wrong = True
            elif gating_labels[result_idx][slot_idx] \
                    == gating_preds[result_idx][slot_idx] \
                    or (slot_eq and
                        gating_preds[result_idx][slot_idx] == ptr_code):
                correct_slots += 1
            else:
                turn_wrong = True
        if not turn_wrong:
            correct_turns += 1

    turn_acc = correct_slots / float(total_slots) if total_slots != 0 else 0
    joint_acc = correct_turns / float(total_turns) if total_turns != 0 else 0
    return joint_acc, turn_acc
