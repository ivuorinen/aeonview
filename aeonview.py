# $Id$
import sys, time, datetime, os, optparse, errno

def aeonview(argv):
	"""Basic settings and configurations for aeonview"""
	parser = optparse.OptionParser(
		usage='Usage: %prog [options]',
		description="aeonview for timelapses",
		version="%prog 0.1.20100718"
	)
	
	basicopts = optparse.OptionGroup(parser,
							"Basic settings",
	                    	"These effect in both modes.")					
	basicopts.add_option(	"-m", "--mode",
							default="image",
							help="run mode: image or video [default: %default]")
	basicopts.add_option(  '-p', '--project',
							help="Project name, used as directory name. "
								"Defaults to 5 characters from md5 hash of the webcam url.",
							type="string" )
	basicopts.add_option(	'-d', '--destination',
							help="Start of the path. Optional, defaults to: .",
							type="string",
							default=".",
							dest="path" )
	parser.add_option_group(basicopts)
	
	# When mode is: image 
	imageopts = optparse.OptionGroup(parser, "Options for mode 'image'",
	                    "When we are gathering images.")					
	imageopts.add_option(	'-u', '--url',
							help="Webcam URL",
							type="string")
	parser.add_option_group(imageopts)
	
	
	# When mode is: video 
	videoopts = optparse.OptionGroup(parser, "Options for mode 'video'",
	                    "When we are making movies.")
	videoopts.add_option(	'-g', '--generate',
							help="Date to video. Format: YYYY-MM-DD. "
								"Default is calculated yesterday, currently %default",
							type="string",
							default=datetime.date.today()-datetime.timedelta(1) )
	videoopts.add_option(	'-r', '--videorun',
							default="daily",
							help="Video to process: daily or monthly [default: %default]",
							type="string")
	videoopts.add_option(   '-f', '--faster',
	                        default="10",
	                        help="Multiplier of video speed, numeric [default: %default]",
	                        type="int")
	parser.add_option_group(videoopts)
	
	
	parser.add_option("-v", help="Verbose", action="store_true", dest="verbose", default=False)
	parser.add_option("-q", help="Quiet", action="store_false", dest="verbose", default=True)
	
	parser.add_option( 		'-s', '--simulate',
							help="Demostrates what will happen "
								"(good for checking your settings and destinations)",
							default=False,
							action="store_true" )
	
	
	(options, args) = parser.parse_args(argv[1:])
	
	if options.simulate == True:
		print
		print "--- Starting simulation, just echoing steps using your parameters."
		print
		print "(!) You are running aeonview from", os.getcwdu(),  "as the user", os.getlogin()
	
	if options.mode == 'image':
		# We are now in the gathering mode.
		
		if options.url == None and options.simulate == True:
			options.url = "http://example.com/webcam.jpg"
			print "(!) Simulation: Using " + options.url + " as webcam url"
	
		if options.url == None:
			print "(!) Need a webcam url, not gonna rock before that!"
			print
			parser.print_help()
			sys.exit(-1)
	
		if options.project == None:
			import hashlib # not needed before
			m = hashlib.md5(options.url).hexdigest()
			options.project = m[:5] # 5 first characters of md5-hash
			if options.verbose == True or options.simulate == True:
				print "(!) No project defined, using part of md5-hash of the webcam url:", options.project
	
		if options.path == None or options.path == ".":
			if options.verbose == True or options.simulate == True:
				print "(!) No destination defined, using:", options.path
		else:
			if options.verbose == True or options.simulate == True:
				print "(!) Using destination:", options.path
	
		# If you want to change the path structure, here's your chance.
		options.imgpath = time.strftime("/img/%Y-%m/%d/")
		options.imgname = time.strftime("%H-%M-%S")
	
		# Let's rock
		options.fileext 	= os.path.splitext(options.url)[1]
		options.destdir 	= options.path + "/" + options.project + options.imgpath
		options.destination = options.destdir + options.imgname + options.fileext
		getit = options.url + " > " + options.destination
	
		# Crude, but works.
		if options.simulate == False:
			mkdir_p( options.destdir )
			os.system('curl --silent %s' % getit)
		else:
			print "(!) Simulation: Making path:", options.destdir
			print "(!) Simulation: curl", getit
			#print options
	
	
	elif options.mode == 'video':
	    
	    if options.faster < 1:
	        options.faster = 1 # Never gonna let you multiply by zero.
	    
		# We are now in the video producing mode
		videofps = options.faster * 25 # = 25fps * multiplier
		vid_extension = ".avi"
		mencoder = os.getcwd() + "/mencoder"
		mencoder = mencoder + " -mf fps="+vidfps+" -nosound -ovc lavc -lavcopts vcodec=mpeg4"
		
		if options.project == None:
			print "(!) No project defined, please specify what project you are working on."
			print
			parser.print_help()
			sys.exit(-1)
			
		
		if options.videorun == "daily":
			#options.generate = "2010-13-01"
		
			vid_date = str(options.generate).split( "-" )
			year 	= vid_date[0]
			month 	= vid_date[1]
			day 	= vid_date[2]
			
			if check_date(int(year), int(month), int(day)):
				video_dir = options.path + "/" + options.project + "/vid/" + year + "-" + month + "/" + day + "/*"
				print "Video dir to process:", video_dir
				video_out_day = options.path + "/" + options.project + "/vid/" + year + "-" + month + "/" + day + vid_extension
				print "Video output-file: ", video_out_day
				print mencoder, "-o", video_out_day, "'mf://"+os.path.dirname( os.path.realpath( video_dir ) ) + "/*'"
			else:
				print "(!) Error: check your date. Value provided:", options.generate
		
		elif options.videorun == "monthly":
			print "Monthly"
		
		else:
			pass
		
		pass
		
	else:
		parser.print_help()
		sys.exit(-1)




# http://stackoverflow.com/questions/600268/mkdir-p-functionality-in-python/600612#600612
def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST:
            pass
        else: raise


# Modified http://markmail.org/message/k2pxsle2lslrmnut
def check_date(year, month, day):
	tup1 = (year, month, day, 0,0,0,0,0,0)
	try:
		date = time.mktime (tup1)
		tup2 = time.localtime (date)
		if tup1[:2] != tup2[:2]:
			return False
		else:
			return True
	except OverflowError:
		return False


if __name__ == '__main__':
	aeonview(sys.argv)