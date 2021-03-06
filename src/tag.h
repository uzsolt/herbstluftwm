#ifndef __HERBSTLUFT_TAG_H_
#define __HERBSTLUFT_TAG_H_

#include <memory>
#include <vector>

#include "attribute_.h"
#include "object.h"
#include "signal.h"

#define TAG_SET_FLAG(tag, flag) \
    ((tag)->flags |= (flag))

enum {
    TAG_FLAG_URGENT = 0x01, // is there a urgent window?
    TAG_FLAG_USED   = 0x02, // the opposite of empty
};

class Client;
class Completion;
class FrameTree;
class Settings;
class Stack;
class TagManager;

class HSTag : public Object {
public:
    HSTag(std::string name, TagManager* tags, Settings* settings);
    ~HSTag() override;
    std::shared_ptr<FrameTree>        frame;  // the master frame
    Attribute_<unsigned long> index;
    Attribute_<bool>         floating;
    Attribute_<bool>         floating_focused; // if a floating client is focused
    Attribute_<std::string>  name;   // name of this tag
    DynAttribute_<int> frame_count;
    DynAttribute_<int> client_count;
    DynAttribute_<int> curframe_windex;
    DynAttribute_<int> curframe_wcount;
    int             flags;
    std::vector<Client*> floating_clients_; //! the clients in floating mode
    size_t               floating_clients_focus_; //! focus in the floating clients
    std::shared_ptr<Stack> stack;
    void setIndexAttribute(unsigned long new_index) override;
    bool focusClient(Client* client);
    void applyFloatingState(Client* client);
    void setVisible(bool visible);
    bool removeClient(Client* client);
    void foreachClient(std::function<void(Client*)> loopBody);
    Client* focusedClient();

    void insertClient(Client* client, std::string frameIndex = {}, bool focus = true);
    Signal needsRelayout_;

    //! add the client's slice to this tag's stack
    void insertClientSlice(Client* client);
    //! remove the client's slice from this tag's stack
    void removeClientSlice(Client* client);

    int focusInDirCommand(Input input, Output output);
    void focusInDirCompletion(Completion& complete);
private:
    void onGlobalFloatingChange(bool newState);
    void fixFocusIndex();
    //! get the number of clients on this tag
    int computeClientCount();
    //! get the number of clients on this tag
    int computeFrameCount();
    Settings* settings_;
};

// for tags
HSTag* find_tag(const char* name);
HSTag* find_tag_with_toplevel_frame(class HSFrame* frame);
HSTag* get_tag_by_index(int index);
int    tag_get_count();
void tag_force_update_flags();
void tag_update_flags();
void tag_set_flags_dirty();

#endif

