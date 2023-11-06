gtkpass
=======

Gtkpass is a simple GUI for the `pass`_ password manager written in Python and
GTK 3.0.


Configuration
-------------

The configuration file is looked at ``$XDG_CONFIG_HOME/gtkpass.yaml`` and is in
yaml format. Currently there is just a plain list of options with their
defaults:

.. code:: yaml

   save_dimension: false
   confirm_recursive_delete: true
   confirm_delete: true
   height: <unspecified>
   weight: <unspecified>

When ``save_dimension`` is set to true, application will save dimension of the
window into ``height`` and ``width``, and pick it up again on program start.

Confirmation are always enabled, as deletion will be instant. Of course, as
`pass`_ is git based, there is always possibility to get deleted items back,
but it should be such question, and both of them can be silenced.

.. _pass: https://www.passwordstore.org
