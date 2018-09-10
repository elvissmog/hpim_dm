from utils import TYPE_CHECKING

if TYPE_CHECKING:
    from .tree_if_upstream import TreeInterfaceUpstream

'''
class SFMRRootState:
    @staticmethod
    def tree_transitions_to_active_state(interface: 'TreeInterfaceUpstream') -> None:
        """
        Tree transitions to Active state AND
        interface roles dont change
        """
        interface.logger.debug('tree_transitions_to_active_state')
        interface.send_my_interest()

    @staticmethod
    def tree_remains_in_active_state_and_non_root_transitions_to_root_interface(interface: 'TreeInterfaceUpstream'):
        """
        Tree remains in Active state AND
        Non-root interface transitions to Root type
        """
        interface.logger.debug('tree_remains_in_active_state_and_non_root_transitions_to_root_interface')
        interface.send_i_am_no_longer_upstream()
        interface.send_my_interest()

    @staticmethod
    def tree_transitions_from_active_to_inactive_state_due_to_transition_from_non_root_to_root_interface(interface: 'TreeInterfaceUpstream'):
        """
        Tree transitions from Active to Inactive state AND
        Non-Root interface transitions to Root type
        """
        interface.logger.debug('tree_transitions_from_active_to_inactive_state_due_to_transition_from_non_root_to_root_interface')
        interface.send_i_am_no_longer_upstream()

    @staticmethod
    def tree_transitions_to_active_state_and_non_root_interface_transitions_to_root(interface: 'TreeInterfaceUpstream') -> None:
        """
        Tree transitions to Active state AND
        Non-Root interface transitions to Root type
        """
        interface.logger.debug('tree_transitions_to_active_state_and_non_root_interface_transitions_to_root')
        SFMRRootState.tree_transitions_to_active_state(interface)

    @staticmethod
    def transition_to_it_or_ot_and_active_tree(interface: 'TreeInterfaceUpstream') -> None:
        """
        Tree is in Active state AND
        interface becomes interested or not interested in receiving data packets
        """
        interface.logger.debug('transition_to_it_or_ot_and_active_tree')
        interface.send_my_interest()

    @staticmethod
    def tree_is_active_and_best_upstream_router_reelected(interface: 'TreeInterfaceUpstream') -> None:
        """
        Tree is in Active state AND
        BestUpstream neighbor changes or BestUpstream neighbor sends an IamUpstream message and remains responsible for
        forwarding data packets
        """
        interface.logger.debug('tree_is_active_and_best_upstream_router_reelected')
        interface.send_my_interest()
'''

class SFMRNewRootState:
    @staticmethod
    def interfaces_roles_change_and_tree_remains_active(interface: 'TreeInterfaceUpstream') -> None:
        """
        Interfaces roles change (NonRoot->Root) AND
        Tree was Active and remains Active
        """
        interface.logger.debug('interfaces_roles_change_and_tree_remains_active')
        interface.send_i_am_no_longer_upstream()
        interface.send_my_interest()

    @staticmethod
    def interfaces_roles_change_and_tree_was_inactive_and_transitions_to_active(interface: 'TreeInterfaceUpstream'):
        """
        Interfaces roles change (NonRoot->Root) AND
        Tree was Inactive and transitions to Active state
        """
        interface.logger.debug('interfaces_roles_change_and_tree_was_inactive_and_transitions_to_active')
        interface.send_my_interest()

    @staticmethod
    def interfaces_roles_change_and_tree_was_active_and_transitions_to_inactive_and_best_upstream_neighbor_is_null(interface: 'TreeInterfaceUpstream'):
        """
        Interfaces roles change (NonRoot->Root) AND
        Tree transitions from Active to Inactive state AND
        BestUpstreamNeighbor is null
        """
        interface.logger.debug('interfaces_roles_change_and_tree_was_active_and_transitions_to_inactive_and_best_upstream_neighbor_is_null')
        interface.send_i_am_no_longer_upstream()

    @staticmethod
    def interfaces_roles_change_and_tree_was_active_and_transitions_to_inactive_and_best_upstream_neighbor_not_null(interface: 'TreeInterfaceUpstream') -> None:
        """
        Interfaces roles change (NonRoot->Root) AND
        Tree transitions from Active to Inactive state AND
        BestUpstreamNeighbor is not null (possible loop detected)
        """
        interface.logger.debug('interfaces_roles_change_and_tree_was_active_and_transitions_to_inactive_and_best_upstream_neighbor_not_null')
        interface.send_i_am_no_longer_upstream()
        interface.send_my_interest()

    @staticmethod
    def interfaces_roles_change_and_tree_remains_inactive_and_best_upstream_neighbor_not_null(interface: 'TreeInterfaceUpstream') -> None:
        """
        Interfaces roles change (NonRoot->Root) AND
        Tree was Inactive and remains Inactive AND
        BestUpstreamNeighbor is not null (possible loop detected)
        """
        interface.logger.debug('interfaces_roles_change_and_tree_remains_inactive_and_best_upstream_neighbor_not_null')
        interface.send_my_interest()

    @staticmethod
    def interfaces_roles_dont_change_and_router_transition_to_it_or_ot(interface: 'TreeInterfaceUpstream') -> None:
        """
        Interfaces roles dont change (this interface remains Root) AND
        BestUpstreamNeighbor does not change AND
        router changes its interest in receiving data packets (becomes interested or not interested)
        """
        interface.logger.debug('interfaces_roles_dont_change_and_router_transition_to_it_or_ot')
        interface.send_my_interest()


    @staticmethod
    def interfaces_roles_dont_change_and_best_upstream_neighbor_reelected(interface: 'TreeInterfaceUpstream') -> None:
        """
        Interfaces roles dont change (this interface remains Root) AND
        BestUpstreamNeighbor changes AND
        BestUpstreamNeighbor is not null
        (other router was elected as the responsible for forwarding multicast data packets)

        OR

        Interfaces roles dont change (this interface remains Root) AND
        BestUpstreamNeighbor transmitted a new IamUpstream message AND
        that neighbor is still responsible for forwarding multicast data packet
        (a new IamUpstream message was received from the BestUpstreamNeighbor but that router is still responsible for
        forwarding multicast data packets)
        """
        interface.logger.debug('tree_is_active_and_best_upstream_router_reelected')
        interface.send_my_interest()
