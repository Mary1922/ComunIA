"""Persistencia JSON sencilla y atómica para incidencias."""

import json
from pathlib import Path
from threading import Lock
from uuid import UUID

from app.core.exceptions import IncidentNotFoundError, PersistenceError
from app.models.schemas import (
    HumanReviewRequest,
    IncidentAction,
    IncidentActionRequest,
    TriageResponse,
)


class IncidentRepository:
    """Repositorio local suficiente para el prototipo del bootcamp."""

    def __init__(self, path: Path | str) -> None:
        self.path = Path(path)
        self._lock = Lock()
        self.path.parent.mkdir(parents=True, exist_ok=True)

        if not self.path.exists():
            self.path.write_text("[]\n", encoding="utf-8")

    def _read_raw(self) -> list[dict]:
        try:
            data = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise PersistenceError(
                "No se ha podido leer data/incidents.json."
            ) from exc

        if not isinstance(data, list):
            raise PersistenceError(
                "data/incidents.json debe contener una lista."
            )
        return data

    def _write_raw(self, data: list[dict]) -> None:
        temp_path = self.path.with_suffix(".tmp")
        try:
            temp_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=2) + "\n",
                encoding="utf-8",
            )
            temp_path.replace(self.path)
        except OSError as exc:
            raise PersistenceError(
                "No se ha podido guardar data/incidents.json."
            ) from exc

    def save(self, response: TriageResponse) -> TriageResponse:
        with self._lock:
            data = self._read_raw()
            data.append(response.model_dump(mode="json"))
            self._write_raw(data)
        return response

    def list_all(self) -> list[TriageResponse]:
        with self._lock:
            data = self._read_raw()

        try:
            return [
                TriageResponse.model_validate(item)
                for item in data
            ]
        except Exception as exc:
            raise PersistenceError(
                "Existe una incidencia almacenada con formato inválido."
            ) from exc

    def get(self, incident_id: UUID) -> TriageResponse:
        """Devuelve una incidencia por su identificador técnico."""

        with self._lock:
            data = self._read_raw()

        for item in data:
            if item.get("incident_id") == str(incident_id):
                return TriageResponse.model_validate(item)

        raise IncidentNotFoundError(
            f"No existe la incidencia {incident_id}."
        )

    def apply_review(
        self,
        incident_id: UUID,
        review: HumanReviewRequest,
    ) -> TriageResponse:
        with self._lock:
            data = self._read_raw()

            for index, item in enumerate(data):
                if item.get("incident_id") != str(incident_id):
                    continue

                current = TriageResponse.model_validate(item)
                updated = current.model_copy(
                    update={
                        "human_status": review.status,
                        "human_classification": review.classification,
                    }
                )
                data[index] = updated.model_dump(mode="json")
                self._write_raw(data)
                return updated

        raise IncidentNotFoundError(
            f"No existe la incidencia {incident_id}."
        )

    def add_action(
        self,
        incident_id: UUID,
        action_request: IncidentActionRequest,
    ) -> TriageResponse:
        """Añade un hito al seguimiento y opcionalmente cambia su estado."""

        with self._lock:
            data = self._read_raw()

            for index, item in enumerate(data):
                if item.get("incident_id") != str(incident_id):
                    continue

                current = TriageResponse.model_validate(item)
                action = IncidentAction(
                    action_type=action_request.action_type,
                    description=action_request.description,
                    actor=action_request.actor,
                    scheduled_for=action_request.scheduled_for,
                )
                updated_actions = [*current.actions, action]
                update_data = {"actions": updated_actions}

                if action_request.new_status is not None:
                    update_data["operational_status"] = action_request.new_status

                updated = current.model_copy(update=update_data)
                data[index] = updated.model_dump(mode="json")
                self._write_raw(data)
                return updated

        raise IncidentNotFoundError(
            f"No existe la incidencia {incident_id}."
        )

