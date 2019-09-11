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
        self.calculate_assert_winner(creating_interface=True)

        # Deal with messages according to tree state and interface role change
        # Event 1
        if not was_root and not previous_tree_state.is_active() and current_tree_state.is_active():
            SFMRNonRootState.interfaces_roles_dont_change_and_tree_transitions_to_active_state(self)
        # Event 2
        elif was_root and current_tree_state.is_active():
            SFMRNonRootState.interfaces_roles_change_and_tree_remains_or_transitions_to_active_state(self)
        # Event 3
        elif previous_tree_state.is_active() and current_tree_state.is_unsure() and best_upstream_router is None:
            SFMRNonRootState.tree_transitions_from_active_to_unsure_and_best_upstream_neighbor_is_null(self)
        # Event 4
        elif previous_tree_state.is_active() and current_tree_state.is_inactive():
            SFMRNonRootState.tree_transitions_from_active_to_inactive(self)
        # Event 5
        elif not was_root and previous_tree_state.is_active() and current_tree_state.is_unsure() and best_upstream_router is not None:
            SFMRNonRootState.interface_roles_dont_change_and_tree_transitions_from_active_to_unsure_and_best_upstream_neighbor_is_not_null(self)
        # Event 6
        elif was_root and previous_tree_state.is_active() and current_tree_state.is_unsure() and best_upstream_router is not None:
            SFMRNonRootState.interface_roles_change_and_tree_transitions_from_active_to_unsure_and_best_upstream_neighbor_is_not_null(self)
        # Event 9
        elif previous_tree_state.is_inactive() and current_tree_state.is_unsure() and best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_inactive_to_unsure_and_best_upstream_is_not_null(self)

        self.logger.debug('Created NonRootInterface')

    ############################################
    # Set ASSERT State
    ############################################
    def calculate_assert_winner(self, creating_interface=False):
        """
        Calculate the router responsible for forwarding data packets to a link...
        Based on this calculation, the Assert state is set
        If tree in Active state and this interface offers a better Assert state compared to all neighbors
            then this interface transitions to AssertWinner state
        If tree in Active state and the BestUpstream neighbor offers a better Assert state (RPC and IP)
            then this interface must transition to AssertLoser state
        If tree in Unsure state and there are no Upstream neighbors connected to this interface
            then this interface transitions to AssertWinner state
        If tree in Unsure state and there are Upstream neighbors connected to this interface
            then this interface transitions to AssertLoser state
        If tree in Inactive state then interface must be in AssertWinner state
        """
        print("CALCULATE ASSERT WINNER")
        if self.is_tree_active():
            if self._best_upstream_router is None:
                self.assert_logger.debug('BEST UPSTREAM NEIGHBOR IS NONE AND TREE IS ACTIVE')
                self.set_assert_state(AssertState.Winner, creating_interface)
            elif self._my_assert_rpc.is_better_than(self._best_upstream_router):
                self.assert_logger.debug('TREE IS ACTIVE AND WON ASSERT')
                self.assert_logger.debug("BEST UPSTREAM NEIGHBOR METRIC_PREFERENCE: " +
                                         str(self._best_upstream_router.metric_preference) + '; METRIC: ' +
                                         str(self._best_upstream_router.route_metric) + '; IP: ' +
                                         self._best_upstream_router.get_ip())
                self.assert_logger.debug("MY METRIC_PREFERENCE: " + str(self._my_assert_rpc.metric_preference) +
                                         '; METRIC: ' + str(self._my_assert_rpc.route_metric) + '; IP: ' +
                                         self._my_assert_rpc.get_ip())
                self.set_assert_state(AssertState.Winner, creating_interface)
            else:
                self.assert_logger.debug('TREE IS ACTIVE AND LOST ASSERT')
                self.assert_logger.debug("BEST UPSTREAM NEIGHBOR METRIC_PREFERENCE: " +
                                         str(self._best_upstream_router.metric_preference) + '; METRIC: ' +
                                         str(self._best_upstream_router.route_metric) + '; IP: ' +
                                         self._best_upstream_router.get_ip())
                self.assert_logger.debug("MY METRIC_PREFERENCE: " + str(self._my_assert_rpc.metric_preference) +
                                         '; METRIC: ' + str(self._my_assert_rpc.route_metric) + '; IP: ' +
                                         self._my_assert_rpc.get_ip())
                self.set_assert_state(AssertState.Loser, creating_interface)
        elif self.is_tree_unsure():
            if self._best_upstream_router is None:
                self.assert_logger.debug('TREE IS UNSURE AND NO UPSTREAM NEIGHBOR')
                self.set_assert_state(AssertState.Winner)
            else:
                self.assert_logger.debug('TREE IS UNSURE AND UPSTREAM NEIGHBOR CONNECTED TO THIS INTERFACE')
                self.set_assert_state(AssertState.Loser, creating_interface)
        else:
            self.assert_logger.debug('TREE IS INACTIVE AND UPSTREAM NEIGHBOR CONNECTED TO THIS INTERFACE')
            self.set_assert_state(AssertState.Winner, creating_interface)

    def set_assert_state(self, new_state: SFMRAssertABC, creating_interface=False):
        """
        Set Assert state (AssertWinner or AssertLoser)
        """
        with self.get_state_lock():
            if new_state != self._assert_state:
                self._assert_state = new_state
                self.assert_logger.debug('Assert state transitions to ' + str(new_state))
                if not creating_interface:
                    self.change_tree()
                    self.evaluate_in_tree()

    ##########################################
    # Set Downstream Node Interest state
    ##########################################
    def set_downstream_node_interest_state(self, new_state: SFMRDownstreamStateABC):
        """
        Set interest state of downstream nodes (DownstreamInterested or NoDownstreamInterested)
        """
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
        """
        The tree of this interface detected that the tree transitioned to Active state
        The interface must react to this change in order to send some control messages
        """
        if not self.is_tree_active():
            super().tree_transition_to_active()
            self.calculate_assert_winner()
            SFMRNonRootState.interfaces_roles_dont_change_and_tree_transitions_to_active_state(self)

    def tree_transition_to_unsure(self):
        """
        The tree of this interface detected that the tree transitioned to Unsure state
        The interface must react to this change in order to send some control messages
        """
        if self.is_tree_active() and self._best_upstream_router is None:
            SFMRNonRootState.tree_transitions_from_active_to_unsure_and_best_upstream_neighbor_is_null(self)
        elif self.is_tree_active() and self._best_upstream_router is not None:
            SFMRNonRootState.interface_roles_dont_change_and_tree_transitions_from_active_to_unsure_and_best_upstream_neighbor_is_not_null(self)
        elif self.is_tree_inactive() and self._best_upstream_router is not None:
            SFMRNonRootState.tree_transitions_from_inactive_to_unsure_and_best_upstream_is_not_null(self)

        if not self.is_tree_unsure():
            super().tree_transition_to_unsure()
            self.calculate_assert_winner()

    def tree_transition_to_inactive(self):
        """
        The tree of this interface detected that the tree transitioned to Inactive state
        The interface must react to this change in order to send some control messages
        """
        if self.is_tree_active():
            SFMRNonRootState.tree_transitions_from_active_to_inactive(self)

        if not self.is_tree_inactive():
            super().tree_transition_to_inactive()
            self.calculate_assert_winner()

    ###########################################
    # Recv packets
    ###########################################
    def recv_data_msg(self):
        """
        This Non-Root interface received a data packet
        """
        return

    def change_best_upstream_neighbor_state(self, new_best_upstream_neighbor_state):
        """
        A neighbor changed Upstream state due to the reception of any control packet
        (IamUpstream or IamNoLongerUpstream or Interest or NoInterest or Sync)
        """
        previous_best_upstream_router = self._best_upstream_router
        super().change_best_upstream_neighbor_state(new_best_upstream_neighbor_state)
        self.calculate_assert_winner()

        # Event 7 and 8
        if self.current_tree_state.is_unsure() and new_best_upstream_neighbor_state is not None and \
                 (previous_best_upstream_router is None or previous_best_upstream_router is not new_best_upstream_neighbor_state):
            SFMRNonRootState.tree_remains_unsure_and_best_upstream_router_reelected(self)

    def change_interest_state(self, interest_state):
        """
        A neighbor has changed Interest state due to the reception of any control packet
        (IamUpstream or IamNoLongerUpstream or Interest or NoInterest or Sync)
        """
        if interest_state:
            self.set_downstream_node_interest_state(SFMRPruneState.DI)
        else:
            self.set_downstream_node_interest_state(SFMRPruneState.NDI)

    ###########################################
    # Send packets
    ###########################################
    def send_i_am_upstream(self):
        """
        Send an IamUpstream message through this interface
        """
        (source, group) = self.get_tree_id()
        if self.get_interface() is not None:
            self.get_interface().send_i_am_upstream(source, group, self._my_assert_rpc)

    def get_sync_state(self):
        """
        Determine if this tree must be included in a new snapshot
        If tree is Active then this must be included in the snapshot, otherwise this tree is not included
        in the snapshot (in this point in time the router is not considered to be Upstream)
        """
        if self.current_tree_state.is_active():
            return self._my_assert_rpc
        else:
            return None

    ##########################################################
    def is_forwarding(self):
        """
        Determine if this interface must be included in the OIL at the multicast routing table
        """
        return self.is_in_tree() and self.is_assert_winner()

    def is_in_tree(self):
        """
        Verify if this interface is connected to interested hosts/nodes
        (based on Interest state of all neighbors and IGMP)
        """
        return self.igmp_has_members() or self.are_downstream_nodes_interested()

    def are_downstream_nodes_interested(self):
        """
        Determine if there is interest from non-Upstream neighbors based on their interest state
        """
        return self._downstream_node_interest_state.are_downstream_nodes_interested()

    def delete(self):
        """
        Tree interface is being removed... due to change of interface roles or
        due to the removal of the tree by this router
        Clear all state from this interface regarding this tree
        """
        super().delete()
        self._my_assert_rpc = None

    def is_assert_winner(self):
        """
        Determine if this interface is responsible for forwarding multicast data packets
        """
        return self._assert_state is not None and self._assert_state.is_assert_winner()

    def notify_rpc_change(self, new_rpc: Metric):
        """
        The router suffered an RPC regarding the subnet of the tree's source
        """
        if new_rpc == self._my_assert_rpc:
            return

        self._my_assert_rpc = AssertMetric(new_rpc.metric_preference, new_rpc.route_metric, self.get_ip())
        if self.current_tree_state.is_active():
            SFMRNonRootState.tree_remains_active_and_my_rpc_changes(self)
        self.calculate_assert_winner()