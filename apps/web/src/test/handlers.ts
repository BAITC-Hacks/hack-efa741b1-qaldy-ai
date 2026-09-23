import { http, HttpResponse } from "msw";
import {
  completionFixture,
  employeeFixture,
  journeyFixture,
} from "./fixtures";

export const apiHandlers = [
  http.get("http://localhost:8000/api/v1/employees", () =>
    HttpResponse.json([employeeFixture]),
  ),
  http.post(
    "http://localhost:8000/api/v1/employees/:employeeId/recommendations",
    () => HttpResponse.json(journeyFixture),
  ),
  http.post(
    "http://localhost:8000/api/v1/employees/:employeeId/activities/:eventId/complete",
    () => HttpResponse.json(completionFixture),
  ),
];
