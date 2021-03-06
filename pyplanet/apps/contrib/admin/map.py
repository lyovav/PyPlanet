"""
Map Admin methods and functions.
"""
import asyncio
import logging

from pyplanet.apps.core.maniaplanet.models import Map
from pyplanet.conf import settings
from pyplanet.contrib.command import Command
from pyplanet.utils import gbxparser

logger = logging.getLogger(__name__)


class MapAdmin:
	def __init__(self, app):
		"""
		:param app: App instance.
		:type app: pyplanet.apps.contrib.admin.app.Admin
		"""
		self.app = app
		self.instance = app.instance

	async def on_start(self):
		await self.instance.permission_manager.register('previous', 'Skip to the previous map', app=self.app, min_level=1)
		await self.instance.permission_manager.register('next', 'Skip to the next map', app=self.app, min_level=1)
		await self.instance.permission_manager.register('restart', 'Restart the maps', app=self.app, min_level=1)
		await self.instance.permission_manager.register('replay', 'Replay the maps', app=self.app, min_level=1)
		await self.instance.permission_manager.register('add_local_map', 'Add map from server disk', app=self.app, min_level=2)
		await self.instance.permission_manager.register('remove_map', 'Remove map from server', app=self.app, min_level=2)
		await self.instance.permission_manager.register('write_map_list', 'Write Matchsettings to file', app=self.app, min_level=2)

		await self.instance.command_manager.register(
			Command(command='next', target=self.next_map, perms='admin:next', admin=True),
			Command(command='skip', target=self.next_map, perms='admin:next', admin=True),
			Command(command='previous', aliases=['prev'], target=self.prev_map, perms='admin:previous', admin=True),
			Command(command='restart', aliases=['res', 'rs'], target=self.restart_map, perms='admin:restart', admin=True),
			Command(command='replay', target=self.replay_map, perms='admin:replay', admin=True),
			Command(command='local', namespace='add', target=self.add_local_map, perms='admin:add_local_map', admin=True)
				.add_param('map', nargs=1, type=str, required=True, help='Map filename (relative to Maps directory).'),
			Command(command='remove', target=self.remove_map, perms='admin:remove_map', admin=True, description='Remove map from maplist.')
				.add_param('nr', required=False, type=int, help='The number from a list window or the unique identifier.'),
			Command(command='erase', target=self.erase_map, perms='admin:remove_map', admin=True, description='Remove and delete map from maplist and disk.')
				.add_param('nr', required=False, type=int, help='The number from a list window or the unique identifier.'),
			Command(command='writemaplist', aliases=['wml'], target=self.write_map_list, perms='admin:write_map_list', admin=True)
				.add_param('file', required=False, type=str, help='Give custom match settings file to save to.')
		)

	async def prev_map(self, player, data, **kwargs):
		if not self.instance.map_manager.previous_map:
			message = '$ff0Error: Previous map is not known'
			return await self.instance.chat(message, player.login)
		if self.instance.map_manager.previous_map == self.instance.map_manager.current_map:
			message = '$ff0Error: Previous map is the same as the current map'
			return await self.instance.chat(message, player.login)

		if 'jukebox' in self.instance.apps.apps:
			self.instance.apps.apps['jukebox'].insert_map(player, self.instance.map_manager.previous_map)
		else:
			await self.instance.map_manager.set_next_map(self.instance.map_manager.previous_map)

		message = '$ff0Admin $fff{}$z$s$ff0 has skipped to the previous map.'.format(player.nickname)
		await self.instance.gbx.multicall(
			self.instance.gbx('NextMap'),
			self.instance.chat(message)
		)

	async def next_map(self, player, data, **kwargs):
		message = '$ff0Admin $fff{}$z$s$ff0 has skipped to the next map.'.format(player.nickname)
		await self.instance.gbx.multicall(
			self.instance.gbx('NextMap'),
			self.instance.chat(message)
		)

	async def restart_map(self, player, data, **kwargs):
		message = '$ff0Admin $fff{}$z$s$ff0 has restarted the map.'.format(player.nickname)
		await self.instance.gbx.multicall(
			self.instance.gbx('RestartMap'),
			self.instance.chat(message)
		)

	async def replay_map(self, player, data, **kwargs):
		if 'jukebox' in self.instance.apps.apps:
			self.instance.apps.apps['jukebox'].insert_map(player, self.instance.map_manager.current_map)
		else:
			await self.instance.map_manager.set_next_map(self.instance.map_manager.current_map)

		await self.instance.chat(
			'$ff0Admin $fff{}$z$s$ff0 has queued this map for replay.'.format(player.nickname)
		)

	async def write_map_list(self, player, data, **kwargs):
		setting = settings.MAP_MATCHSETTINGS
		if isinstance(setting, dict) and self.instance.process_name in setting:
			setting = setting[self.instance.process_name]
		if not isinstance(setting, str):
			setting = None

		if not setting and not data.file:
			message = '$ff0Default match settings file not configured in your settings!'
			return await self.instance.chat(message, player)
		if data.file:
			file_name = data.file
		else:
			file_name = setting.format(server_login=self.instance.game.server_player_login)

		file_path = 'MatchSettings/{}'.format(file_name)
		message = '$ff0Match Settings has been saved to the file: {}'.format(file_name)
		await self.instance.map_manager.save_matchsettings(file_path)

		# Send message + reload all maps in memory.
		await asyncio.gather(
			self.instance.chat(message, player),
			self.instance.map_manager.update_list(full_update=True)
		)

	async def add_local_map(self, player, data, **kwargs):
		map_file = data.map

		if not await self.instance.storage.driver.exists('UserData/Maps/{}'.format(
			map_file
		)):
			message = '$ff0Error: Can\'t add map because the file is not found!'
			await self.instance.chat(message, player.login)
			return

		try:
			# Parse GBX file.
			async with self.instance.storage.open_map(map_file) as map_fh:
				parser = gbxparser.GbxParser(buffer=map_fh)
				map_info = await parser.parse()

			# Test if map isn't yet in our current map list.
			if self.instance.map_manager.playlist_has_map(map_info['uid']):
				raise Exception('Map already in playlist! Update? remove it first!')

			# Insert map to server.
			result = await self.instance.map_manager.add_map(map_file)

			if result:
				message = '$ff0Admin $fff{}$z$s$ff0 has added the map $fff{}$z$s$ff0 by $fff{}$z$s$ff0.'.format(
					player.nickname, map_info['name'], map_info['author_nickname']
				)
				await self.instance.chat(message)
			else:
				raise Exception('Unknown error while adding the map!')
		except Exception as e:
			logger.warning('Error when player {} was adding map from local disk: {}'.format(player.login, str(e)))
			message = '$ff0Error: Can\'t add map, Error: {}'.format(str(e))
			await self.instance.chat(message, player.login)

	async def erase_map(self, player, data, **kwargs):
		kwargs['erase'] = True
		return await self.remove_map(player, data, **kwargs)

	async def remove_map(self, player, data, **kwargs):
		map_nr = getattr(data, 'nr', None)
		erase = kwargs.get('erase', False)

		try:
			# Make sure we get the map instance.
			if not map_nr:
				map_instance = self.instance.map_manager.current_map
			else:
				map_instance = await Map.get(id=map_nr)

			# Send remove command.
			await self.instance.map_manager.remove_map(map_instance, delete_file=erase)

			# Send message to all.
			message = '$ff0Admin $fff{}$z$s$ff0 has removed the map $fff{}$z$s$ff0.'.format(
				player.nickname, map_instance.name
			)
			await self.instance.chat(message)
		except Exception as e:
			# Handle errors.
			logger.error(str(e))
			message = '$ff0Error: Can\'t remove map, Error: {}'.format(str(e))
			await self.instance.chat(message, player)
