// Receive real Gazebo Transport camera messages and save one verified RGB frame.
#include <atomic>
#include <chrono>
#include <fstream>
#include <functional>
#include <iostream>
#include <mutex>
#include <thread>
#include <gz/transport/Node.hh>
#include <gz/msgs/image.pb.h>
#include <gz/common/Image.hh>
int main(int argc,char **argv){
  if(argc!=4){std::cerr<<"camera_subscriber TOPIC OUTPUT.png RESULT.json\n";return 2;}
  gz::transport::Node node;std::atomic<int> count{0};std::mutex mutex;gz::msgs::Image latest;
  std::function<void(const gz::msgs::Image&)> receive=[&](const gz::msgs::Image&image){
    if(!image.width()||!image.height()||image.data().size()!=size_t(image.width())*image.height()*3)return;
    std::lock_guard<std::mutex> lock(mutex);latest=image;++count;
  };
  if(!node.Subscribe(argv[1],receive)){std::cerr<<"Could not subscribe\n";return 3;}
  auto deadline=std::chrono::steady_clock::now()+std::chrono::seconds(240);
  while(count<3&&std::chrono::steady_clock::now()<deadline)std::this_thread::sleep_for(std::chrono::milliseconds(100));
  if(count<3){std::cerr<<"Expected three RGB image messages; got "<<count<<"\n";return 4;}
  std::lock_guard<std::mutex> lock(mutex);gz::common::Image image;
  image.SetFromData(reinterpret_cast<const unsigned char*>(latest.data().data()),latest.width(),latest.height(),gz::common::Image::RGB_INT8);
  image.SavePNG(argv[2]);std::ofstream report(argv[3]);
  report<<"{\"received_images\":"<<count<<",\"width\":"<<latest.width()<<",\"height\":"<<latest.height()<<"}\n";
  std::cout<<"TRANSPORT CAMERA PASS: "<<count<<" images "<<latest.width()<<"x"<<latest.height()<<"\n";
  return 0;
}
