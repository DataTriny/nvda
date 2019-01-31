#accPropServer.py
#A part of NonVisual Desktop Access (NVDA)
#Copyright (C) 2017-2018 NV Access Limited, Derek Riemer, Babbage B.V.
#This file is covered by the GNU General Public License.
#See the file COPYING for more details.

"""Implementation of IAccProcServer, so that customization of a wx control can be done very fast."""

from logHandler import log
from  comtypes.automation import VT_EMPTY
from  comtypes import COMObject
from comInterfaces.Accessibility import IAccPropServer, ANNO_CONTAINER, ANNO_THIS
from abc import ABCMeta, abstractmethod
from six import with_metaclass
import weakref
import winUser
import wx

class IAccPropServer_Impl(with_metaclass(ABCMeta, COMObject)):
	"""Base class for implementing a COM interface for a hwnd based AccPropServer\
	to annotate a WX control.
	This should eventually be dropped in favor of WX' own annotation support,
	blocked by wxWidgets/Phoenix#1129.
	Please override the _GetPropValue method, not GetPropValue.
	GetPropValue wraps _getPropValue to catch and log exceptions (Which for some reason NVDA's logger misses when they occur in GetPropValue).
	"""

	_com_interfaces_ = [
		IAccPropServer
	]

	def __init__(self, control, properties, annotateChildren=True):
		"""Initialize the instance of AccPropServer. 
		@param control: the WX control instance, so you can look up things in the _getPropValue method.
			It's available on self.control.
		@Type control: Subclass of wx.Window
		@param properties: an array of properties that is to be handled by this isntance.
		@type properties: L{comtypes.GUID}*n
		@param annotateChildren: whether the WX control is a container which children should be annotated.
		@type annotateChildren: bool
		"""
		self.control = weakref.ref(control)
		self.hwnd = control.GetHandle()
		self.properties = properties
		super(IAccPropServer_Impl, self).__init__()
		# Import late to avoid circular import
		from IAccessibleHandler import accPropServices
		accPropServices.SetHwndPropServer(
			hwnd=self.hwnd,
			idObject=winUser.OBJID_CLIENT,
			idChild=0,
			paProps=properties,
			cProps=len(properties),
			pServer=self,
			AnnoScope=ANNO_CONTAINER if annotateChildren else ANNO_THIS
		)
		# clean up of the accPropServices needs to happen when the control is destroyed.
		control.Bind(wx.EVT_WINDOW_DESTROY, self._onDestroyControl, source=control)

	@abstractmethod
	def _getPropValue(self, pIDString, dwIDStringLen, idProp):
		"""use this method to implement GetPropValue. It  is wrapped by the callback GetPropValue to handle exceptions.
		For instructions on implementing accPropServers, see https://msdn.microsoft.com/en-us/library/windows/desktop/dd373681(v=vs.85).aspx .
		For instructions specifically about this method, see see https://msdn.microsoft.com/en-us/library/windows/desktop/dd318495(v=vs.85).aspx .
		@param pIDString: Contains a string that identifies the property being requested.
			If a single callback object is registered for annotating multiple accessible elements,
			the identity string can be used to determine which element the request refers to.
			If the accessible element is HWND-based,
			IAccessibleHandler.accPropServices.DecomposeHwndIdentityString can be used
			to extract the HWND/idObject/idChild from the identity string.
			Note that, while one IAccPropServer implementation can annotate
			multiple accessible elements, it is still bound to one wx.Control.
		@type pIDString: str
		@param dwIDStringLen: Specifies the length of the identity string specified by the pIDString parameter.
		@type dwIDStringLen: int
		@param idProp: Specifies a GUID indicating the desired property.
		@type idProp: One of the oleacc.PROPID_* GUIDS
		"""
		raise NotImplementedError

	def GetPropValue(self, pIDString, dwIDStringLen, idProp):
		try:
			return self._getPropValue(pIDString, dwIDStringLen, idProp)
		except Exception:
			log.exception()
			return VT_EMPTY, 0

	def _onDestroyControl(self, evt):
		evt.Skip() # Allow other handlers to process this event.
		self._cleanup()

	def _cleanup(self):
		# Import late to avoid circular import
		from IAccessibleHandler import accPropServices
		accPropServices.ClearHwndProps(
			hwnd=self.hwnd,
			idObject=winUser.OBJID_CLIENT,
			idChild=0,
			paProps=self.properties,
			cProps=len(self.properties)
		)
