from openprocurement.api.utils import get_now, handle_store_exceptions, context_unpack
from openprocurement.api.auth import extract_access_token
from openprocurement.tender.core.procedure.context import get_now
from jsonpatch import make_patch, apply_patch
from jsonpointer import resolve_pointer
from hashlib import sha512
from uuid import uuid4
from logging import getLogger
from datetime import datetime


LOGGER = getLogger(__name__)


def get_first_revision_date(document, default=None):
    revisions = document.get("revisions") if document else None
    return datetime.fromisoformat(revisions[0]["date"]) if revisions else default


def set_ownership(item, request):
    if not item.get("owner"):  # ???
        item["owner"] = request.authenticated_userid
    token, transfer = uuid4().hex, uuid4().hex
    item["owner_token"] = token
    item["transfer_token"] = sha512(transfer.encode("utf-8")).hexdigest()
    access = {"token": token, "transfer": transfer}
    return access


def delete_nones(data: dict):
    for k, v in tuple(data.items()):
        if v is None:
            del data[k]


def save_tender(request, modified: bool = True) -> bool:
    tender = request.validated["tender"]

    # TODO move this to post tender view
    # if tender.get("mode") == "test":
    #     set_mode_test_titles(tender)

    patch = get_revision_changes(tender, request.validated["tender_src"])
    if patch:
        now = get_now()
        append_tender_revision(request, tender, patch, now)

        old_date_modified = tender.get("dateModified", now.isoformat())
        if modified:
            tender["dateModified"] = now.isoformat()

        with handle_store_exceptions(request):
            uid, rev = request.registry.db.save(tender)
            tender["rev"] = rev
            LOGGER.info(
                "Saved tender {}: dateModified {} -> {}".format(
                    uid,
                    old_date_modified,
                    tender["dateModified"]
                ),
                extra=context_unpack(request, {"MESSAGE_ID": "save_tender"}, {"RESULT": rev}),
            )
            return True
    return False


def append_tender_revision(request, tender, patch, date):
    status_changes = [p for p in patch if all([
        not p["path"].startswith("/bids/"),
        p["path"].endswith("/status"),
        p["op"] == "replace"
    ])]
    for change in status_changes:
        obj = resolve_pointer(tender, change["path"].replace("/status", ""))
        if obj and hasattr(obj, "date"):
            date_path = change["path"].replace("/status", "/date")
            if obj.date and not any([p for p in patch if date_path == p["path"]]):
                patch.append({"op": "replace", "path": date_path, "value": obj.date.isoformat()})
            elif not obj.date:
                patch.append({"op": "remove", "path": date_path})
            obj.date = date
    return append_revision(request, tender, patch)


def append_revision(request, obj, patch):
    revision_data = {
        "author": request.authenticated_userid,
        "changes": patch,
        "rev": obj.rev,
        "date": get_now().isoformat(),
    }
    if "revisions" not in obj:
        obj["revisions"] = []
    obj["revisions"].append(revision_data)
    return obj["revisions"]


def get_revision_changes(dst, src):
    result = make_patch(dst, src).patch
    return result


def set_mode_test_titles(item):
    for key, prefix in (
        ("title", "ТЕСТУВАННЯ"),
        ("title_en", "TESTING"),
        ("title_ru", "ТЕСТИРОВАНИЕ"),
    ):
        if not item.get(key) or prefix not in item[key]:
            item[key] = f"[{prefix}] {item.get('key') or ''}"


# GETTING/SETTING sub documents ---

def get_items(request, parent, key, uid):
    items = tuple(i for i in parent.get(key, "") if i["id"] == uid)
    if items:
        return items
    else:
        from openprocurement.api.utils import error_handler
        obj_name = "document" if "Document" in key else key.rstrip('s')
        request.errors.add("url", f"{obj_name}_id", "Not Found")
        request.errors.status = 404
        raise error_handler(request)


def set_item(parent, key, uid, value):
    assert value["id"] == uid, "Assigning item by id with a different id ?"
    initial_list = parent.get(key, "")
    # in case multiple documents we update the latest
    for n, item in enumerate(reversed(initial_list), 1):
        if item["id"] == uid:
            initial_list[-1 * n] = value
            break
    else:
        raise AssertionError(f"Item with id {uid} unexpectedly not found")
# --- GETTING/SETTING sub documents


# ACL ---
def is_item_owner(request, item):
    acc_token = extract_access_token(request)
    return request.authenticated_userid == item["owner"] and acc_token == item["owner_token"]
# --- ACL


# PATCHING ---
def apply_tender_patch(request, data, src, save=True, modified=True):
    patch = apply_data_patch(src, data)
    # src now contains changes,
    # it should link to request.validated["tender"]
    if patch and save:
        return save_tender(request, modified=modified)


def apply_data_patch(item, changes):
    patch_changes = []
    prepare_patch(patch_changes, item, changes)
    if not patch_changes:
        return {}
    r = apply_patch(item, patch_changes)
    return r


def prepare_patch(changes, orig, patch, basepath=""):
    if isinstance(patch, dict):
        for i in patch:
            if i in orig:
                prepare_patch(changes, orig[i], patch[i], "{}/{}".format(basepath, i))
            else:
                changes.append({"op": "add", "path": "{}/{}".format(basepath, i), "value": patch[i]})
    elif isinstance(patch, list):
        if len(patch) < len(orig):
            for i in reversed(list(range(len(patch), len(orig)))):
                changes.append({"op": "remove", "path": "{}/{}".format(basepath, i)})
        for i, j in enumerate(patch):
            if len(orig) > i:
                prepare_patch(changes, orig[i], patch[i], "{}/{}".format(basepath, i))
            else:
                changes.append({"op": "add", "path": "{}/{}".format(basepath, i), "value": j})
    else:
        for x in make_patch(orig, patch).patch:
            x["path"] = "{}{}".format(basepath, x["path"])
            changes.append(x)

# --- PATCHING
