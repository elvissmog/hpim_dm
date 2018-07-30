import logging

import Main
from .tree_interface import TreeInterface
from .non_root_state_machine import SFMRNonRootState
from .assert_state import AssertState, SFMRAssertABC
from .downstream_state import SFMRPruneState, SFMRDownstreamStateABC
from .metric import AssertMetric, Metric


class TreeInterfaceDownstream(TreeInterface):
    LOGGER = logging.getLogger('protocol.KernelEntry.NonRootInterface')

    def __init__(self, kernel_entry, interface_id, rpc: Metric, best_upstream_router, interest_state, was_root, previous_tree_state, current_tree_state):
        extra_dict_logger = kernel_entry.kernel_entry_logger.extra.copy()
        extra_dict_logger['vif'] = interface_id
        extra_dict_logger['interfacename'] = Main.kernel.vif_index_to_name_dic[interface_id]
        logger = logging.LoggerAdapter(TreeInterfaceDownstream.LOGGER, extra_dict_logger)
        TreeInterface.__init__(self, kernel_entry, interface_id, best_upstream_router, current_tree_state, logger)
        self.assert_logger = logging.LoggerAdapter(logger.logger.getChild('Assert'), logger.extra)
        self.downstream_logger = logging.LoggerAdapter(logger.logger.getChild('Downstream'), logger.extra)

        # Downstream Node Interest State
        if interest_state:
            self._downstream_node_interest_state = SFMRPruneState.DI
        else:
            self._downstream_node_interest_state = SFMRPruneState.NDI
        self.downstream_logger.debug('Downstream interest state transitions to ' + str(self._downstream_node_interest_state))

        # Assert Winner State
        self._assert_state = AssertState.Winner
        self.assert_logger.debug('Assert state transitions to ' + str(self._assert_state))
        self._my_assert_rpc = AssertMetric(rpc.metric_preference, rpc.route_metric, self.get_ip())
        self.calculate_assert_winner()

        # Deal with messages according to tree state and interface role change
        # Event 1
        if not was_root and not previous_tree_state.is_active() and current_tree_state.is_active():
            SFMRNonRootState.interfaces_roles_dont_change_and_tree_transitions_to_active_state(self)
        # Event 2
        elif was_root and current_tree_state.is_active():
            SFMRNonRootState.interfaces_roles_change_and_tree_remains_or_transitions_to_active_state(self)
        # Event 3
        elif previous_tree_state.is_active() and current_tree_state.is_inactive() and best_upstream_router is None:
            SFMRNonRootState.tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_null(self)
        # Event 4
        elif previous_tree_state.is_active() and current_tree_state.is_unknown():
            SFMRNonRootState.tree_transitions_from_active_to_unknown(self)
        # Event 5
        elif previous_tree_state.is_active() and current_tree_state.is_inactive() and best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_not_null(self)
        # Event 8
        elif previous_tree_state.is_unknown() and current_tree_state.is_inactive() and best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_unknown_to_inactive_and_best_upstream_is_not_null(self)

        self.logger.debug('Created NonRootInterface')

    ############################################
    # Set ASSERT State
    ############################################
    def calculate_assert_winner(self):
        print("CALCULATE ASSERT WINNER")
        if self._best_upstream_router is None:
            self.assert_logger.debug('BEST UPSTREAM NEIGHBOR IS NONE')
            self.set_assert_state(AssertState.Winner)
        elif self._my_assert_rpc.is_better_than(self._best_upstream_router):
            self.assert_logger.debug('WON ASSERT')
            self.assert_logger.debug("BEST UPSTREAM NEIGHBOR METRIC_PREFERENCE: " +
                                     str(self._best_upstream_router.metric_preference) + '; METRIC: ' +
                                     str(self._best_upstream_router.route_metric) + '; IP: ' +
                                     self._best_upstream_router.get_ip())
            self.assert_logger.debug("MY METRIC_PREFERENCE: " + str(self._my_assert_rpc.metric_preference) +
                                     '; METRIC: ' + str(self._my_assert_rpc.route_metric) + '; IP: ' +
                                     self._my_assert_rpc.get_ip())
            self.set_assert_state(AssertState.Winner)
        else:
            self.assert_logger.debug('LOST ASSERT')
            self.assert_logger.debug("BEST UPSTREAM NEIGHBOR METRIC_PREFERENCE: " +
                                     str(self._best_upstream_router.metric_preference) + '; METRIC: ' +
                                     str(self._best_upstream_router.route_metric) + '; IP: ' +
                                     self._best_upstream_router.get_ip())
            self.assert_logger.debug("MY METRIC_PREFERENCE: " + str(self._my_assert_rpc.metric_preference) +
                                     '; METRIC: ' + str(self._my_assert_rpc.route_metric) + '; IP: ' +
                                     self._my_assert_rpc.get_ip())
            self.set_assert_state(AssertState.Loser)

    def set_assert_state(self, new_state: SFMRAssertABC):
        with self.get_state_lock():
            if new_state != self._assert_state:
                self._assert_state = new_state
                self.assert_logger.debug('Assert state transitions to ' + str(new_state))

                self.change_tree()
                self.evaluate_in_tree()

    ##########################################
    # Set Downstream Node Interest state
    ##########################################
    def set_downstream_node_interest_state(self, new_state: SFMRDownstreamStateABC):
        with self.get_state_lock():
            if new_state != self._downstream_node_interest_state:
                self._downstream_node_interest_state = new_state
                self.downstream_logger.debug('Downstream interest state transitions to ' + str(new_state))

                self.change_tree()
                self.evaluate_in_tree()

    ############################################
    # Tree transitions
    ############################################
    def tree_transition_to_active(self):
        if not self.is_tree_active():
            SFMRNonRootState.interfaces_roles_dont_change_and_tree_transitions_to_active_state(self)

        super().tree_transition_to_active()

    def tree_transition_to_inactive(self):
        if self.is_tree_active() and self._best_upstream_router is None:
            SFMRNonRootState.tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_null(self)
        elif self.is_tree_active() and self._best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_not_null(self)
        elif self.is_tree_unknown() and self._best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_unknown_to_inactive_and_best_upstream_is_not_null(self)

        super().tree_transition_to_inactive()

    def tree_transition_to_unknown(self):
        if self.is_tree_active():
            SFMRNonRootState.tree_transitions_from_active_to_unknown(self)

        super().tree_transition_to_unknown()

    ###########################################
    # Recv packets
    ###########################################
    def recv_data_msg(self):
        return

    def change_assert_state(self, assert_state):
        best_upstream_router = self._best_upstream_router
        super().change_assert_state(assert_state)
        self.calculate_assert_winner()

        '''
        if best_upstream_router is None and assert_state is not None or \
                best_upstream_router is not None and assert_state is None or \
                best_upstream_router is not assert_state:
            self._downstream_state.tree_is_inactive_and_best_upstream_router_reelected(self)
        '''
        # Event 6 and 7
        if self.current_tree_state.is_inactive() and assert_state is not None and \
                 (best_upstream_router is None or best_upstream_router is not assert_state):
            SFMRNonRootState.tree_remains_inactive_and_best_upstream_router_reelected(self)

    def change_interest_state(self, interest_state):
        if interest_state:
            self._downstream_node_interest_state.in_tree(self)
        else:
            self._downstream_node_interest_state.out_tree(self)

    ###########################################
    # Send packets
    ###########################################
    def send_i_am_upstream(self):
        (source, group) = self.get_tree_id()
        if self.get_interface() is not None:
            self.get_interface().send_i_am_upstream(source, group, self._my_assert_rpc)

    def get_sync_state(self):
        if self.current_tree_state.is_active():
            return self._my_assert_rpc
        else:
            return None

    ##########################################################

    # Override
    def is_forwarding(self):
        return self.is_in_tree() and self.is_assert_winner()

    def is_in_tree(self):
        return self.igmp_has_members() or self.are_downstream_nodes_interested()

    def are_downstream_nodes_interested(self):
        return self._downstream_node_interest_state == SFMRPruneState.DI

    # Override
    def delete(self):
        super().delete()
        self._my_assert_rpc = None

    def is_assert_winner(self):
        return self._assert_state is not None and self._assert_state.is_assert_winner()

    def notify_rpc_change(self, new_rpc: Metric):
        if new_rpc == self._my_assert_rpc:
            return

        self._my_assert_rpc = AssertMetric(new_rpc.metric_preference, new_rpc.route_metric, self.get_ip())
        if self.current_tree_state.is_active():
            SFMRNonRootState.tree_is_active_and_my_rpc_changes(self)
        self.calculate_assert_winner()
