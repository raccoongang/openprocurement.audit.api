.. _Dialogue:

Post
====

Schema
------

:title:
   string, required

:description:
   string, required

:documents:
   List of :ref:`document` objects

:datePublished:
   string, :ref:`date`, autogenerated

:dateOverdue:
   string, :ref:`date`, autogenerated

:postOf:
    string, autogenerated

    Possible values for :ref:`decision` or :ref:`conclusion` are:

    * `decision`
    * `conclusion`

:relatedPost:
    string

    Id of related :ref:`post`.

:relatedParty:
    string

    Id of related :ref:`party`.

:author:
    string, autogenerated

    Possible values are:

    * `monitoring_owner`
    * `tender_owner`
