from jinja2 import Environment, PackageLoader, select_autoescape

from pyplanet.core.ui.loader import PyPlanetLoader


async def load_template(file):
	return Template(file)


class Template:
	"""
	Template class manages the template file source and the rendering of it.
	
	Will also take care of the loader of the Jinja2 template engine.
	
	Some notable prefixes:
	
	- core.views: ``pyplanet.views.templates``.
	- core.pyplanet: ``pyplanet.apps.core.pyplanet.templates``.
	- core.maniaplanet: ``pyplanet.apps.core.pyplanet.templates``.
	- core.trackmania: ``pyplanet.apps.core.trackmania.templates``.
	- core.shootmania: ``pyplanet.apps.core.shootmania.templates``.
	- [app_label]: ``[app path]/templates``.
	"""

	def __init__(self, file):

		self.file = file
		self.env = Environment(
			loader=PyPlanetLoader.get_loader(),
			autoescape=select_autoescape(['html', 'xml', 'Txt', 'txt', 'ml', 'ms', 'script.txt', 'Script.Txt']),
		)
		self.template = self.env.get_template(file)

	async def render(self, **data):
		return self.template.render(**data)
