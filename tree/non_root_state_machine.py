from utils import TYPE_CHECKING

if TYPE_CHECKING:
    from .tree_if_downstream import TreeInterfaceDownstream


class SFMRNonRootState:
    @staticmethod
    def interfaces_roles_dont_change_and_tree_transitions_to_active_state(interface: 'TreeInterfaceDownstream') -> None:
        """
        Tree transitions to Active state AND
        interface roles dont change
        """
        interface.logger.debug('interfaces_roles_dont_change_and_tree_transitions_to_active_state')
        interface.send_i_am_upstream()

    @staticmethod
    def interfaces_roles_change_and_tree_remains_or_transitions_to_active_state(interface: 'TreeInterfaceDownstream') -> None:
        """
        Tree remains or changes to Active state AND
        interface roles change (Root->Non-Root)
        """
        interface.logger.debug('interfaces_roles_change_and_tree_remains_or_transitions_to_active_state')
        interface.send_i_am_upstream()

    @staticmethod
    def tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_null(interface: 'TreeInterfaceDownstream'):
        """
        Tree transitions from Active to Inactive state AND
        BestUpstream neighbor is null
        """
        interface.logger.debug('tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_null')
        interface.send_i_am_no_longer_upstream()

    @staticmethod
    def tree_transitions_from_active_to_unknown(interface: 'TreeInterfaceDownstream'):
        """
        Tree transitions from Active to Unknown state
        """
        interface.logger.debug('tree_transitions_from_active_to_unknown')
        interface.send_i_am_no_longer_upstream()

    @staticmethod
    def tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_not_null(interface: 'TreeInterfaceDownstream'):
        """
        Tree transitions from Active to Inactive state AND
        BestUpstream neighbor is not null
        """
        interface.logger.debug('tree_transitions_from_active_to_inactive_and_best_upstream_neighbor_is_not_null')
        interface.send_i_am_no_longer_upstream()
        interface.send_no_interest()

    @staticmethod
    def tree_remains_inactive_and_best_upstream_router_reelected(interface: 'TreeInterfaceDownstream'):
        """
        Tree remains in Inactive state AND
        BestUpstream neighbor changes

        OR

        Tree remains in Inactive state AND
        BestUpstream neighbor transmitted IamUpstream message that doesnt cause a change of the BestUpstream neighbor
        """
        interface.logger.debug('interfaces_roles_dont_change_and_tree_transitions_to_active_state')
        interface.send_no_interest()

    @staticmethod
    def tree_transitions_from_unknown_to_inactive_and_best_upstream_is_not_null(interface: 'TreeInterfaceDownstream'):
        """
        Tree transitions from Unknown to Inactive state AND
        BestUpstream neighbor is not null
        """
        interface.logger.debug('tree_transitions_from_unknown_to_inactive_and_best_upstream_is_not_null')
        interface.send_no_interest()

    @staticmethod
    def tree_is_active_and_my_rpc_changes(interface: 'TreeInterfaceDownstream') -> None:
        """
        Tree is Active AND
        MyRPC changes
        """
        interface.logger.debug('tree_is_active_and_my_rpc_changes')
        interface.send_i_am_upstream()
