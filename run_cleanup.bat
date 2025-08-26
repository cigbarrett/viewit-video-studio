@echo off
title AI Video Cleanup
echo.
echo CLEANUP TOOL               
echo                                        
echo Removes old files to free up space  
echo (older than 6 hours)                
echo.
echo  Press any key to start cleanup...
pause >nul

echo.
echo  Cleaning up old files...
python cleanup_old_files.py

echo.
echo  Cleanup complete!
echo.
pause
