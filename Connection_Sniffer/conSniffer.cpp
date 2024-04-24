/******************************************************************************/
/*                                                                            */
/* FILE:        conSniffer.cpp                                                */
/*                                                                            */
/* DESCRIPTION:   This program monitors the operational status of two         */
/*HMI devices by listening for their heartbeat signals over the network.      */
/*sing ZeroMQ for messaging, it concurrently tracks each HMI through          */
/*separate threads, printing a notification for each received heartbeat to    */
/*indicate the device's active connection.  This tool aids in the early       */
/*detection of connectivity issues or failures in systems where               */
/*continuous HMI operation is crucial.                                        */
/*                                                                            */
/* AUTHOR(S): Tyler Worley                                                    */
/* Company: Henny Penny                                                       */
/*                                                                            */
/* DATE:        2/23/2024                                                     */
/*                                                                            */
/*                                                                            */
/*                                                                            */
/* EDIT HISTORY:                                                              */
/* 2/12/2024 - Initial release                                                */
/* 2/21/2024 - Updated                                                        */
/*                                                                            */
/******************************************************************************/

#include <zmq.h>          // Include ZeroMQ library
#include <pthread.h>      // Include POSIX threads library
#include <signal.h>       // Include signal handling library (for graceful shutdown)
#include <string.h>       // Include string handling functions
#include <stdio.h>        // Include standard I/O functions
#include <stdlib.h>       // Include standard library functions
#include <atomic>         // Include atomic operations library
#include <unistd.h>       // Include POSIX API for Unix systems
#include <string>         // Include string class

// Global flag to control running state of threads
std::atomic<bool> running(true);

struct HMIThreadData {
    HMIConnection conn;
    int* timeoutCounter;
}

// Structure to hold Human-Machine Interface (HMI) connection information
struct HMIConnection {
    std::string address;    // Full ZeroMQ address to connect to
    std::string identifier; // Human-readable identifier for the HMI

    // Constructor: Prepends "tcp://" to the given address
    HMIConnection(const std::string& addr, const std::string& id)
        : identifier(id), address("tcp://" + addr) {}
};

struct BBBConnection {
    std::string address;
    std::string identifier;

    BBBConnection(const std::string& addr, const std:: string& id)
        : identifier(id), address("tcp://" + addr) {}
};

// Signal handler function to stop the program gracefully
void handle_signals(int signum) {
    running = false; // Set running flag to false on signal reception
}

void* bbbStatusListener(void* arg) {
    BBBConnection* conn = static_cast<BBBConnection*>(arg);

    void* context = zmq_ctx_new();
    void* subscriber = zmq_socket(context, ZMQ_SUB);
    const char* filter = "";
    zmq_setsockopt(subscriber,ZMQ_SUBSCRIBE, filter, strlen(filter));
    zmq_connect(subscriber, conn->address.c_str());
    
    static int bbbTimeoutCounter = 0;
    while(running) {
        zmq_msg_t message;
        zmq_msg_init(&message);
        if (zmq_msg_recv(&message, subscriber, ZMQ_DONTWAIT) != -1) {
            // Process the BBB status message here
            printf("Status received from %s\n", conn->identifier.c_str(), ". BBB is connected.\n");
            bbbTimeoutCounter = 0; 
        }
        else if(++bbbTimeoutCounter > 50) {
            bbbTimeoutCounter = 0;
            printf("!!!!Status not received from %s. BBB IS NOT CONNECTED!!!!\n" , conn->identifier.c_str());
        }
        zmq_msg_close(&message);
        usleep(100000);
    }
    zmq_close(subscriber);
    zmq_ctx_destroy(context);
    delete(conn);
    pthread_exit(NULL);
}

// Thread function to listen for heartbeats from an HMI
void* hmiHeartbeatListener(void* arg) {
    HMIThreadData* data = static_cast<HMIThreadData*>(arg);
    // Initialize ZeroMQ context and subscriber socket
    void* context = zmq_ctx_new();
    void* subscriber = zmq_socket(context, ZMQ_SUB);

    // Subscribe to all incoming messages
    const char* filter = "";
    zmq_setsockopt(subscriber, ZMQ_SUBSCRIBE, filter, strlen(filter));

    // Connect to the HMI's ZeroMQ address
    zmq_connect(subscriber, data->conn.address.c_str());

    // Listen for messages as long as the running flag is true
    while (running) {
        zmq_msg_t message;
        zmq_msg_init(&message);
        // Non-blocking receive to keep checking the running flag
        if (zmq_msg_recv(&message, subscriber, ZMQ_DONTWAIT) != -1) {
            // Print a message when a heartbeat is received
            printf("Heartbeat received from %s HMI. %s HMI IS CONNECTED.\n", conn->identifier.c_str(), conn->identifier.c_str());
            *(data->timeoutCounter) = 0; // Reset timeout counter. 
        }
        else if (++(*(data->timeoutCounter)) > 20) {
            *(data->timeoutCounter) = 0; // Reset timeout counter.
             printf("!!!!Heartbeat not received from %s HMI. %s HMI IS NOT CONNECTED!!!!\n", data->conn.identifier.c_str(), data->conn.identifier.c_str());
        }
        zmq_msg_close(&message);
        usleep(100000); // Wait for 100 milliseconds to reduce CPU usage
    }

    // Clean up ZeroMQ resources
    zmq_close(subscriber);
    zmq_ctx_destroy(context);
    delete data; // Delete dynamically allocated memory to avoid leaks
    pthread_exit(NULL); // Exit the thread
}

int main(int argc, char* argv[]) {
    // Check for correct command line arguments
    if (argc != 4) {
        fprintf(stderr, "Usage: %s <HMI1_IP:PORT> <HMI2_IP:PORT> <BBB_IP:PORT>\n", argv[0]);
        return EXIT_FAILURE;
    }
    int hmi1TimeoutCounter = 0;
    int hmi2TimeoutCounter = 0;

    // Set up signal handling for graceful shutdown
    signal(SIGINT, handle_signals);
    signal(SIGTERM, handle_signals);

    // Create threads for each HMI connection and BBB
    pthread_t hmi1ListenerThread, hmi2ListenerThread, bbbStatusThread;

    // Initialize connection objects with provided addresses and identifiers
    HMIThreadData* data1 = new HMIThreadData{HMIConnection(argv[1], "Primary"), &hmi1TimeoutCounter};
    HMIThreadData* data2 = new HMIThreadData{HMIConnection(argv[2], "Secondary"), &hmi2TimeoutCounter};

    // Initialize BBB connection object with provided address and identifier
    BBBConnection* bbbConn = new BBBConnection(argv[3], "BBB");

    // Start threads to listen for heartbeats from each HMI
    if (pthread_create(&hmi1ListenerThread, NULL, hmiHeartbeatListener, data1) != 0) {
        fprintf(stderr, "Error creating thread for HMI 1 listener\n");
        delete data1;
        delete data2;
        delete bbbConn;
        return EXIT_FAILURE;
    }

    if (pthread_create(&hmi2ListenerThread, NULL, hmiHeartbeatListener, data2) != 0) {
        fprintf(stderr, "Error creating thread for HMI 2 listener\n");
        delete data1; // Prevent memory leak by deleting the first connection
        delete data2;
        delete bbbConn;
        return EXIT_FAILURE;
    }

    // Start thread to listen for status messages from the BBB
    if ( pthread_create(&bbbStatusThread, NULL, bbbStatusListener, bbbConn) != 0) {
        fprintf(stderr, "Error creating thread for BBB status listener\n");
        delete data1;
        delete data2;
        delete bbbConn;
        return EXIT_FAILURE;
    }

    // Wait for HMI and BBB threads to finish
    pthread_join(hmi1ListenerThread, NULL);
    pthread_join(hmi2ListenerThread, NULL);
    pthread_join(bbbStatusThread, NULL);

    // Clean up dynamically allocated memory
    delete data1;
    delete data2;
    delete bbbConn;

    return EXIT_SUCCESS; // Program exited successfully
}
