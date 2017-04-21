from peewee import DoesNotExist

from pyplanet.apps.core.maniaplanet.models import Player
from pyplanet.apps.core.pyplanet.models import Permission
from pyplanet.core.events import receiver
from pyplanet.core import signals


class PermissionManager:
	def __init__(self, instance):
		"""
		Initiate, should only be done from the core instance.
		:param instance: Instance.
		:type instance: pyplanet.core.instance.Instance
		"""
		self._instance = instance

		# Initiate the self instances on receivers.
		self.handle_startup()

	@receiver(signals.pyplanet_start_apps_before)
	async def handle_startup(self, **kwargs):
		"""
		Handle startup, just before the apps will start. We will make sure we are ready to get requests for permissions
		:param kwargs: Ignored parameters.
		"""
		pass

	async def has_permission(self, player, permission):
		"""
		Check if the player has the right permission.
		:param player: player instance.
		:param permission: permission name.
		:return: boolean if player is allowed.
		"""
		if isinstance(permission, str):
			perm_namespace, _, perm_name = permission.rpartition(':')
			permission = await self.get_perm(name=perm_name, namespace=perm_namespace)
		if isinstance(player, str):
			player = await self._instance.player_manager.get_player(login=player)
		if not isinstance(permission, Permission):
			raise Exception('Permission should be a string or permission object!')
		if not isinstance(player, Player):
			raise Exception('Player should be a string or player object!')
		return player.level >= permission.min_level

	async def get_perm(self, namespace, name):
		return await Permission.get(namespace=namespace, name=name)

	async def register(self, name, description='', app=None, min_level=1, namespace=None):
		"""
		Register a new permission.
		:param name: Name of permission
		:param description: Description in english.
		:param app: App instance to retrieve the label.
		:param min_level: Minimum level required.
		:param namespace: Namespace, only for core usage!
		:return: Permission instance.
		"""
		if not namespace and app:
			namespace = app.label
		if not namespace:
			raise Exception('Namespace is required. You should give your app instance with app=app instead!')

		try:
			perm = await self.get_perm(namespace=namespace, name=name)
		except DoesNotExist:
			perm = Permission(namespace=namespace, name=name, description=description, min_level=min_level)
			await perm.save()
		return perm