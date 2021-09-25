from Inference.inference import Inference


# video = 'files/gate_mission1.mp4'
video = 'C:\\Users\\Luka0\\Documents\\Python\\GateDataGathering\\buoy_videos\\buoy1.MOV'
# video = 'C:\\Users\\Luka0\\Documents\\Python\\GateDataGathering\\gate_videos\\gate_mission1.mp4'
inference = Inference(video)  # Pass wither a video path or camera index

# inference.run_gate_detector()
# inference.run_object_detection(model_name='postmodel', objects=['post'], tracking=True)
inference.run_object_detection(model_name='buoymodel', objects=['badge', 'tommy'], tracking=True)
# inference.run_object_detection(model_name='models', objects=['remote'], tracking=False)
