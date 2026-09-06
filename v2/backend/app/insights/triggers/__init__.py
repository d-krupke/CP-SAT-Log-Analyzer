"""One module per topic; every ``Trigger`` subclass in here becomes an Overview box.

Module names are free - discovery is by import, not by name - but the ``order``
of a trigger decides where its box appears:

* ``10`` quality of the log itself (truncated, unrecognized lines): what is said
  here changes how much the rest is worth, so it comes first
* ``20`` the outcome (status, gap)
* ``30`` how the run progressed over time
* ``40`` what the search statistics show
* ``50`` (default) everything else
* ``60`` the solution hint
* ``70`` what presolve did to the model

Ties keep definition order within a module.
"""
