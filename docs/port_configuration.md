## Diagram
`image goes here`

Priveledged Port | Protocol |Function
---------------- | ---------------- | ----------------
50001 | Socket | Video Stream `HOST <-> Inference`
50002 | Socket | Logging Messages `HOST <-> Intelligence`
50003 | Socket | Sensor Telemetry `HOST <-> Control`
50004 | Socket | Pilot Input Controls `HOST <-> Control`
50051 | GRPC | Comms Intelligence and Inference `Intelligence <-> Inference`
50052 | GRPC | Host Command `HOST <-> Intelligence`
65432 | Socket | Video Pipe to Intelligence `Intelligence <- Inference`
