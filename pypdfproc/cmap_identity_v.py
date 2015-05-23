"""
Identity-V CMap to convert character codes to unicode.

From https://github.com/adobe-type-tools/cmap-resources/blob/master/cmapresources_identity-0.zip
"""

from .parser import CMapTokenizer

class CMapIdentityV:
	mapper = None

	def __init__(self):
		if CMapIdentityV.mapper == None:
			CMapIdentityV.mapper = CMapTokenizer().BuildMapper(CMapIdentityV.cmap_identity_v)

		self.CMapper = CMapIdentityV.mapper

	cmap_identity_v = """
%!PS-Adobe-3.0 Resource-CMap
%%DocumentNeededResources: ProcSet (CIDInit)
%%IncludeResource: ProcSet (CIDInit)
%%BeginResource: CMap (Identity-V)
%%Title: (Identity-V Adobe Identity 0)
%%Version: 10.004
%%Copyright: -----------------------------------------------------------
%%Copyright: Copyright 1990-2015 Adobe Systems Incorporated.
%%Copyright:
%%Copyright: Licensed under the Apache License, Version 2.0 (the
%%Copyright: "License"); you may not use this file except in
%%Copyright: compliance with the License. You may obtain a copy of
%%Copyright: the License at
%%Copyright: http://www.apache.org/licenses/LICENSE-2.0.html
%%Copyright:
%%Copyright: Unless required by applicable law or agreed to in
%%Copyright: writing, software distributed under the License is
%%Copyright: distributed on an "AS IS" BASIS, WITHOUT WARRANTIES OR
%%Copyright: CONDITIONS OF ANY KIND, either express or implied. See
%%Copyright: the License for the specific language governing
%%Copyright: permissions and limitations under the License.
%%Copyright: -----------------------------------------------------------
%%EndComments

/CIDInit /ProcSet findresource begin

12 dict begin

begincmap

/CIDSystemInfo 3 dict dup begin
/Registry (Adobe) def
/Ordering (Identity) def
/Supplement 0 def
end def

/CMapName /Identity-V def
/CMapVersion 10.004 def
/CMapType 1 def

/XUID [1 10 25404 9991] def

/WMode 1 def

/Identity-H usecmap

endcmap
CMapName currentdict /CMap defineresource pop
end
end

%%EndResource
%%EOF
"""

