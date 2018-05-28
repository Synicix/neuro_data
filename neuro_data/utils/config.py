from inspect import isclass
from pprint import pformat

import datajoint as dj
from .data import key_hash, to_native
from .. import logger as log

class ConfigBase:
    _config_type = None

    @property
    def definition(self):
        return """
        # parameters for {cn}

        {ct}_hash                   : varchar(256) # unique identifier for configuration
        {extra_foreign} 
        ---
        {ct}_description            : varchar(2048) # description of the config
        {ct}_type                   : varchar(50)  # type
        {ct}_ts=CURRENT_TIMESTAMP : timestamp      # automatic
        """.format(ct=self._config_type, cn=self.__class__.__name__,
                   extra_foreign=self._extra_foreign if hasattr(self, '_extra_foreign') else '')

    def fill(self):
        type_name = self._config_type + '_type'
        hash_name = self._config_type + '_hash'
        with self.connection.transaction:
            for rel in [getattr(self, member) for member in dir(self)
                        if isclass(getattr(self, member)) and issubclass(getattr(self, member), dj.Part)]:
                log.info('Checking' + rel.__name__)
                for key in rel().content:
                    key[type_name] = rel.__name__
                    key[hash_name] = key_hash(key)

                    if not key in rel().proj():
                        self.insert1(dict(key, **{self._config_type + '_description':rel.describe(key)}),
                                     ignore_extra_fields=True)
                        log.info('Inserting\n' + pformat(key, indent=20))
                        rel().insert1(key,ignore_extra_fields=True)

    def parameters(self, key, selection=None):
        type_name = self._config_type + '_type'
        key = (self & key).fetch1()  # complete parameters
        part = getattr(self, key[type_name])
        ret = (self * part() & key).fetch1()
        ret = to_native(ret)
        if selection is None:
            del ret[self._config_type + '_ts']
            del ret[self._config_type + '_hash']
            return ret
        else:
            if isinstance(selection, list):
                return tuple(ret[k] for k in selection)
            else:
                return ret[selection]