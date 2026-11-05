// Fast Reminders access for weekly.py (AppleScript takes 90+ s on the 1,300-item Shopping list).
// rem read <list> [--open]          -> JSON [{name,id,done,body}]
// rem ensure <list>                 -> creates the list in the iCloud account if missing
// rem add <list>  (JSON on stdin)   -> [{name,body}] added
// rem complete <list> (JSON stdin)  -> [id] checked off (never deleted)
// rem reopen <list> (JSON stdin)    -> [id] unchecked
// rem notes <list> (JSON stdin)     -> [{id,body}] sets each reminder's notes
// rem get <list> (JSON stdin)       -> [id] -> [{id,done}] (a deleted reminder is left out)
import EventKit
import Foundation

let store = EKEventStore()
let sem = DispatchSemaphore(value: 0)
var ok = false
store.requestFullAccessToReminders { granted, _ in ok = granted; sem.signal() }
sem.wait()
guard ok else { FileHandle.standardError.write("no Reminders access\n".data(using: .utf8)!); exit(2) }

let args = CommandLine.arguments
let cmd = args[1], name = args[2]
func list(_ n: String) -> EKCalendar? { store.calendars(for: .reminder).first { $0.title == n } }
func out(_ o: Any) { print(String(data: try! JSONSerialization.data(withJSONObject: o, options: .fragmentsAllowed), encoding: .utf8)!) }
func stdinJSON() -> Any { try! JSONSerialization.jsonObject(with: FileHandle.standardInput.readDataToEndOfFile()) }

switch cmd {
case "read":
    guard let cal = list(name) else { out(NSNull()); exit(0) }
    let pred = args.contains("--open")
        ? store.predicateForIncompleteReminders(withDueDateStarting: nil, ending: nil, calendars: [cal])
        : store.predicateForReminders(in: [cal])
    var rows: [[String: Any]] = []
    store.fetchReminders(matching: pred) { rs in
        rows = (rs ?? []).map { ["name": $0.title ?? "", "id": $0.calendarItemIdentifier, "done": $0.isCompleted, "body": $0.notes ?? ""] }
        sem.signal()
    }
    sem.wait(); out(rows)
case "ensure":
    if list(name) == nil {
        let cal = EKCalendar(for: .reminder, eventStore: store)
        cal.title = name
        cal.source = store.defaultCalendarForNewReminders()?.source
        try! store.saveCalendar(cal, commit: true)
    }
    out(true)
case "add":
    guard let cal = list(name) else { exit(3) }
    var made: [EKReminder] = []
    for x in stdinJSON() as! [[String: String]] {
        let r = EKReminder(eventStore: store)
        r.calendar = cal; r.title = x["name"]; r.notes = x["body"]
        try! store.save(r, commit: false)
        made.append(r)
    }
    try! store.commit(); out(made.map { $0.calendarItemIdentifier })
case "complete":
    for id in stdinJSON() as! [String] {
        if let r = store.calendarItem(withIdentifier: id) as? EKReminder { r.isCompleted = true; try! store.save(r, commit: false) }
    }
    try! store.commit(); out(true)
case "reopen":
    for id in stdinJSON() as! [String] {
        if let r = store.calendarItem(withIdentifier: id) as? EKReminder { r.isCompleted = false; try! store.save(r, commit: false) }
    }
    try! store.commit(); out(true)
case "notes":
    for x in stdinJSON() as! [[String: String]] {
        if let r = store.calendarItem(withIdentifier: x["id"]!) as? EKReminder { r.notes = x["body"]; try! store.save(r, commit: false) }
    }
    try! store.commit(); out(true)
case "get":
    out((stdinJSON() as! [String]).compactMap { id -> [String: Any]? in
        guard let r = store.calendarItem(withIdentifier: id) as? EKReminder else { return nil }
        return ["id": id, "done": r.isCompleted]
    })
default:
    exit(1)
}
