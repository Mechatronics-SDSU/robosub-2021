from Inference.inference import Inference


video = 'files/gate_mission1.mp4'
inference = Inference(video)  # Pass wither a video path or camera index

# inference.run_gate_detector()
inference.run_object_detection(model_name='postmodel', objects=['post', 'cell phone'], tracking=True)
# inference.run_object_detection(model_name='model', objects=['remote'], tracking=False)


